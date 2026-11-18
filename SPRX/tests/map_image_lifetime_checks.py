"""Exercise production custom-image retirement, tombstones and native slot reuse."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "SPRX/t7_mapimages.cpp").read_text(encoding="utf-8")


def extract(marker):
    start = SOURCE.rindex(marker)
    opening = SOURCE.index("{", start)
    depth = 0
    for i in range(opening, len(SOURCE)):
        if SOURCE[i] == "{":
            depth += 1
        elif SOURCE[i] == "}":
            depth -= 1
            if depth == 0:
                return SOURCE[start:i + 1]
    raise ValueError(f"unterminated block: {marker}")


PICTURE_LOOKUP = extract("static Picture* PictureByAddress(")
STILL_OURS = extract("static bool StillOurs(")
RETIRE_PICTURE = extract("static bool RetirePicture(")
LIVE_STOCK = extract("static bool IsLiveStockImage(")
PICTURE_FOR = extract("static uint64_t PictureFor(")
ELEMENT_ARGUMENT = extract("static uint64_t ElementArgument(")
SET_IMAGE = extract("static uint64_t SetImage_h(")

assert "g_retiredPictureCount >= kRetiredPictureMax" in RETIRE_PICTURE
assert "g_retiredPictures[g_retiredPictureCount++] = picture" in RETIRE_PICTURE
assert "if (!RetirePicture(picture))" in PICTURE_FOR
assert PICTURE_FOR.index("if (!RetirePicture(picture))") < PICTURE_FOR.index("picture.image = 0")
assert "PictureByAddress(image, &retired)" in SET_IMAGE
assert "IsLiveStockImage(image)" in SET_IMAGE
assert "g_findAsset ? g_findAsset(kImageType, \"$white\", 0, 0) : 0" in SET_IMAGE

PREFIX = r"""
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <climits>
using Hook_t = uint64_t (*)(uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,
                            double,double,double,double,double,double,double,double);
using FindAsset_t = uint64_t (*)(uint64_t,const char*,uint64_t,uint64_t);
static constexpr size_t kSlotName=304, kSlotInUse=368;
static constexpr size_t kStateTop=72, kStateBase=80;
static constexpr uint32_t kTypeLightUserdata=2, kTypeUserdata=7;
static constexpr uint32_t kMaxElements=0x4E20;
static constexpr int kMaxPictures=128;
static constexpr uint32_t kRetiredPictureMax=1024;
static constexpr uintptr_t kGenerations=0x1000, kElements=0x2000, kStreamedDraw=0x7000;
static constexpr int kImageType=9;
static constexpr size_t kImageStreamed=250, kElementFlags=16, kElementImage=208;
static constexpr size_t kElementStreaming=216, kElementUpdate=272;
struct Picture { char name[96]; uint64_t image; uint64_t retryAfter; bool failureLogged; };
static uintptr_t g_base;
static Picture g_pictures[1];
static int g_pictureCount=1;
static Picture g_retiredPictures[kRetiredPictureMax];
static uint32_t g_retiredPictureCount=0;
static bool g_retiredPictureLimitLogged=false;
static FindAsset_t g_findAsset=nullptr;
static void* g_setImageOriginal=nullptr;
static uint64_t SetImage_h(uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,
                           double,double,double,double,double,double,double,double);
static bool RangeReadable(uintptr_t p,size_t n) { return p != 0 && n != 0; }
static void T7Log_Write(const char*, ...) {}
static bool IsPictureName(const char* name) { return std::strncmp(name,"custom_preview_",15)==0; }
static unsigned nativeCalls=0, whiteLookups=0;
static bool whiteAvailable=true;
static uint64_t expected[6];
static uint8_t whiteImage[512];
static uint64_t Native(uint64_t a,uint64_t b,uint64_t c,uint64_t d,uint64_t e,uint64_t f,
                       double x0,double x1,double x2,double x3,double x4,double x5,double x6,double x7)
{
    const uint64_t got[]={a,b,c,d,e,f};
    for(unsigned i=0;i<6;++i) assert(got[i]==expected[i]);
    const double xs[]={x0,x1,x2,x3,x4,x5,x6,x7};
    for(unsigned i=0;i<8;++i) assert(xs[i]==(double)i+0.5);
    ++nativeCalls;
    return 0xC0FFEE;
}
static uint64_t FindAsset(uint64_t type,const char* name,uint64_t error,uint64_t wait)
{
    assert(type==kImageType && error==0 && wait==0);
    assert(std::strcmp(name,"$white")==0);
    ++whiteLookups;
    return whiteAvailable ? (uintptr_t)whiteImage : 0;
}
static uint64_t RetryPicture(Picture& picture) { return picture.image; }
""" + PICTURE_LOOKUP + "\n" + STILL_OURS + "\n" + RETIRE_PICTURE + "\n" + LIVE_STOCK + "\n" + PICTURE_FOR + r"""
static uint64_t ElementArgument(uint64_t L)
""" + ELEMENT_ARGUMENT[ELEMENT_ARGUMENT.index("{"):] + r"""
static uint64_t SetImage_h(uint64_t a1,uint64_t a2,uint64_t a3,uint64_t a4,uint64_t a5,uint64_t a6,
                           double x0,double x1,double x2,double x3,double x4,double x5,double x6,double x7)
""" + SET_IMAGE[SET_IMAGE.index("{"):] + r"""
static void PrepareState(uint8_t* state,uint8_t* stack,uint8_t* handle,uint16_t generation)
{
    *(uint64_t*)(state+kStateBase)=(uintptr_t)stack;
    *(uint64_t*)(state+kStateTop)=(uintptr_t)(stack+48);
    *(uint32_t*)stack=kTypeLightUserdata;
    *(uint64_t*)(stack+8)=(uintptr_t)handle;
    *(uint16_t*)handle=3;
    *(uint16_t*)(handle+2)=generation;
}
static uint64_t Invoke(uint8_t* state,uint8_t* stack,uint64_t image)
{
    *(uint32_t*)(stack+16)=kTypeLightUserdata;
    *(uint64_t*)(stack+24)=image;
    for(unsigned i=0;i<6;++i) expected[i]=0x100+i;
    expected[0]=(uintptr_t)state;
    return SetImage_h(expected[0],expected[1],expected[2],expected[3],expected[4],expected[5],
                      0.5,1.5,2.5,3.5,4.5,5.5,6.5,7.5);
}
static void SetSlot(uint8_t* image,const char* name,bool inUse)
{
    *(uint8_t*)(image+kSlotInUse)=inUse ? 1 : 0;
    std::memset(image+kSlotName,0,64);
    std::snprintf((char*)(image+kSlotName),64,"%s",name);
}
int main()
{
    static uint8_t globals[0x10000];
    static uint8_t state[128], stack[64], handle[8], customImage[512], nextCustom[512], stockImage[512];
    g_base=(uintptr_t)globals;
    g_findAsset=FindAsset;
    g_setImageOriginal=(void*)Native;
    std::strcpy(g_pictures[0].name,"custom_preview_test");
    g_pictures[0].image=(uintptr_t)customImage;
    SetSlot(customImage,"custom_preview_test",true);
    SetSlot(nextCustom,"custom_preview_test",true);
    *(uint8_t*)(whiteImage+kImageStreamed)=0;
    *(uint16_t*)(g_base+kGenerations+2*3)=9;
    *(uint64_t*)(g_base+kElements+408*3+kElementUpdate)=g_base+kStreamedDraw;
    PrepareState(state,stack,handle,9);

    // A currently owned custom image is assigned without native forwarding.
    *(uint64_t*)(g_base+kElements+408*3+kElementImage)=0x1111;
    *(uint8_t*)(g_base+kElements+408*3+kElementFlags)=2;
    *(uint16_t*)(g_base+kElements+408*3+kElementStreaming)=0;
    assert(Invoke(state,stack,(uintptr_t)customImage)==0);
    assert(*(uint64_t*)(g_base+kElements+408*3+kElementImage)==(uintptr_t)customImage);
    assert((*(uint8_t*)(g_base+kElements+408*3+kElementFlags)&2)==0);
    assert(*(uint16_t*)(g_base+kElements+408*3+kElementStreaming)==255);
    assert(nativeCalls==0 && whiteLookups==0);

    // PictureFor retires the address before clearing/reusing the active record.
    SetSlot(customImage,"",false);
    assert(PictureFor("custom_preview_test")==0);
    assert(g_pictures[0].image==0 && g_retiredPictureCount==1);
    assert(g_retiredPictures[0].image==(uintptr_t)customImage);
    g_pictures[0].image=(uintptr_t)nextCustom;
    SetSlot(nextCustom,"custom_preview_test",true);

    // Delayed callbacks still find the tombstone after the active record has
    // been reused and replace the retired pointer with the native white image.
    for(unsigned i=0;i<100;++i)
    {
        *(uint64_t*)(g_base+kElements+408*3+kElementImage)=0x2222;
        assert(Invoke(state,stack,(uintptr_t)customImage)==0);
        assert(*(uint64_t*)(g_base+kElements+408*3+kElementImage)==(uintptr_t)whiteImage);
    }
    assert(whiteLookups==100 && nativeCalls==0);

    // If the allocator reused the old address for a live stock image, preserve
    // the native call and exact argument/result contract.
    SetSlot(customImage,"stock_image",true);
    assert(Invoke(state,stack,(uintptr_t)customImage)==0xC0FFEE);
    assert(nativeCalls==1 && whiteLookups==100);

    // Reuse for a different custom preview is not stock: fail closed to white.
    SetSlot(customImage,"custom_preview_other",true);
    *(uint64_t*)(g_base+kElements+408*3+kElementImage)=0x3333;
    assert(Invoke(state,stack,(uintptr_t)customImage)==0);
    assert(*(uint64_t*)(g_base+kElements+408*3+kElementImage)==(uintptr_t)whiteImage);
    assert(nativeCalls==1 && whiteLookups==101);

    // A stale element generation is rejected before white lookup or native call.
    *(uint16_t*)(handle+2)=8;
    *(uint64_t*)(g_base+kElements+408*3+kElementImage)=0x4444;
    assert(Invoke(state,stack,(uintptr_t)customImage)==0);
    assert(*(uint64_t*)(g_base+kElements+408*3+kElementImage)==0x4444);
    assert(nativeCalls==1 && whiteLookups==101);
    *(uint16_t*)(handle+2)=9;

    // Untracked stock images retain native arguments and return values.
    assert(Invoke(state,stack,(uintptr_t)stockImage)==0xC0FFEE);
    assert(nativeCalls==2);

    // Capacity exhaustion never overwrites old tombstones or drops the active
    // ownership record. New custom images are refused, but stale callbacks are
    // still recognized and never forwarded to native.
    std::memset(g_retiredPictures,0,sizeof(g_retiredPictures));
    for(uint32_t i=0;i<kRetiredPictureMax;++i)
        g_retiredPictures[i].image=0x100000 + (uint64_t)i*0x1000;
    g_retiredPictureCount=kRetiredPictureMax;
    g_pictures[0].image=(uintptr_t)customImage;
    SetSlot(customImage,"",false);
    assert(PictureFor("custom_preview_test")==0);
    assert(g_pictures[0].image==(uintptr_t)customImage);
    bool wasRetired=false;
    assert(PictureByAddress(0x100000,&wasRetired)!=nullptr && wasRetired);
    assert(PictureByAddress(0x100000 + (uint64_t)(kRetiredPictureMax-1)*0x1000,&wasRetired)!=nullptr && wasRetired);
    *(uint64_t*)(g_base+kElements+408*3+kElementImage)=0x5555;
    assert(Invoke(state,stack,(uintptr_t)customImage)==0);
    assert(g_pictures[0].image==(uintptr_t)customImage);
    assert(*(uint64_t*)(g_base+kElements+408*3+kElementImage)==(uintptr_t)whiteImage);
    assert(nativeCalls==2);

    std::puts("PASS: live custom image, post-reuse tombstone callbacks, stock slot reuse, stale generation and fail-closed registry exhaustion");
}
"""

with tempfile.TemporaryDirectory(prefix="bo3-image-lifetime-") as directory:
    directory = Path(directory)
    source = directory / "image_lifetime.cpp"
    binary = directory / "image_lifetime"
    source.write_text(PREFIX, encoding="utf-8")
    subprocess.run([
        "g++", "-std=c++20", "-Wall", "-Wextra", "-Werror", "-O1",
        "-fsanitize=address,undefined", str(source), "-o", str(binary)
    ], check=True)
    subprocess.run([str(binary)], check=True, timeout=30)

print("PASS: retired custom-image callback lifetime and fail-closed registry")
