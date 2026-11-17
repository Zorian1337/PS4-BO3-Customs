"""Exercise production SetImage_h against retired/reused custom-image slots."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "t7_mapimages.cpp").read_text()


def extract_block(source, marker):
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    for i in range(opening, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
    raise ValueError(f"unterminated block: {marker}")


PICTURE_LOOKUP = extract_block(SOURCE, "static Picture* PictureByAddress(")
STILL_OURS = extract_block(SOURCE, "static bool StillOurs(")
RETIRE_PICTURE = extract_block(SOURCE, "static void RetirePicture(")
ELEMENT_ARGUMENT = extract_block(SOURCE, "static uint64_t ElementArgument(")
SET_IMAGE = extract_block(SOURCE, "static uint64_t SetImage_h(")

PREFIX = r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <climits>
using Hook_t = uint64_t (*)(uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,
                            double,double,double,double,double,double,double,double);
using FindAsset_t = uint64_t (*)(uint64_t,const char*,uint64_t,uint64_t);
static constexpr size_t kSlotName=304, kSlotInUse=368;
static constexpr size_t kStateTop=72, kStateBase=80;
static constexpr uint32_t kTypeLightUserdata=2, kTypeUserdata=7;
static constexpr uint32_t kMaxElements=0x4E20;\nstatic constexpr int kRetiredPictureMax=256;
static constexpr uintptr_t kGenerations=0x1000, kElements=0x2000, kStreamedDraw=0x7000, kFindAsset=0x8000;
static constexpr int kImageType=9;
static constexpr size_t kImageStreamed=250, kElementFlags=16, kElementImage=208;
static constexpr size_t kElementStreaming=216, kElementUpdate=272;
struct Picture { char name[96]; uint64_t image; uint64_t retryAfter; bool failureLogged; };
static uintptr_t g_base;
static Picture g_pictures[1];
static int g_pictureCount=1;
static FindAsset_t g_findAsset=nullptr;
static void* g_setImageOriginal=nullptr;
static uint64_t SetImage_h(uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,
                           double,double,double,double,double,double,double,double);
static bool RangeReadable(uintptr_t p,size_t) { return p != 0; }
static unsigned nativeCalls=0, whiteLookups=0;\nstatic bool whiteAvailable=true;
static uint64_t expected[6];
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
static uint8_t whiteImage[512];
static uint64_t FindAsset(uint64_t type,const char* name,uint64_t error,uint64_t wait)
{
    assert(type==kImageType && error==1 && wait==0);
    assert(std::strcmp(name,"$white")==0);
    ++whiteLookups;
    return whiteAvailable ? (uintptr_t)whiteImage : 0;
}
static void PrepareState(uint8_t* state,uint8_t* stack,uint8_t* handle,uint16_t generation)
{
    *(uint64_t*)(state+kStateBase)=(uintptr_t)stack;
    *(uint64_t*)(state+kStateTop)=(uintptr_t)(stack+48);
    *(uint32_t*)stack=kTypeLightUserdata;
    *(uint64_t*)(stack+8)=(uintptr_t)handle;
    *(uint16_t*)handle=3;
    *(uint16_t*)(handle+2)=generation;
    *(uint32_t*)(stack+16)=kTypeLightUserdata;
    *(uint64_t*)(stack+24)=g_pictures[0].image;
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
'''

MAIN = r'''
int main()
{
    static uint8_t globals[0x10000];
    static uint8_t state[128], stack[64], handle[8], customImage[512], stockImage[512];
    g_base=(uintptr_t)globals;
    g_findAsset=FindAsset;
    g_setImageOriginal=(void*)Native;
    std::strcpy(g_pictures[0].name,"custom");
    g_pictures[0].image=(uintptr_t)customImage;
    *(uint8_t*)(customImage+kSlotInUse)=1;
    std::strcpy((char*)(customImage+kSlotName),"custom");
    *(uint16_t*)(g_base+kGenerations+2*3)=9;
    *(uint64_t*)(g_base+kElements+408*3+kElementUpdate)=g_base+kStreamedDraw;
    PrepareState(state,stack,handle,9);

    // Current custom slot ownership permits the direct image assignment.
    *(uint64_t*)(g_base+kElements+408*3+kElementImage)=0x1111;
    *(uint8_t*)(g_base+kElements+408*3+kElementFlags)=2;
    *(uint16_t*)(g_base+kElements+408*3+kElementStreaming)=0;
    assert(Invoke(state,stack,(uintptr_t)customImage)==0);
    assert(*(uint64_t*)(g_base+kElements+408*3+kElementImage)==(uintptr_t)customImage);
    assert((*(uint8_t*)(g_base+kElements+408*3+kElementFlags)&2)==0);
    assert(*(uint16_t*)(g_base+kElements+408*3+kElementStreaming)==255);
    assert(nativeCalls==0);

    // Retired/reused slot: resolve the native white asset without waiting and
    // never forward the stale custom pointer to the original method.
    *(uint8_t*)(customImage+kSlotInUse)=0;
    *(char*)(customImage+kSlotName)=0;
    *(uint8_t*)(whiteImage+kImageStreamed)=0;
    *(uint64_t*)(g_base+kElements+408*3+kElementImage)=0x2222;
    assert(Invoke(state,stack,(uintptr_t)customImage)==0);
    assert(g_pictures[0].image==0 && g_pictures[0].retryAfter==0);
    assert(*(uint64_t*)(g_base+kElements+408*3+kElementImage)==(uintptr_t)whiteImage);
    assert(whiteLookups==1 && nativeCalls==0);
    assert(g_retiredPictures[0].image==(uintptr_t)customImage);

    // Repeated delayed callbacks keep matching the tombstone and never reach
    // the native method after the active Picture record has been cleared.
    for (unsigned i=0;i<100;++i)
    {
        assert(Invoke(state,stack,(uintptr_t)customImage)==0);
        assert(*(uint64_t*)(g_base+kElements+408*3+kElementImage)==(uintptr_t)whiteImage);
    }
    assert(whiteLookups==101 && nativeCalls==0);

    // A reused slot with another name is rejected even if the native white
    // fallback is unavailable; no stale write or native forwarding occurs.
    g_pictures[0].image=(uintptr_t)customImage;
    *(uint8_t*)(customImage+kSlotInUse)=1;
    std::strcpy((char*)(customImage+kSlotName),"other");
    whiteAvailable=false;
    *(uint64_t*)(g_base+kElements+408*3+kElementImage)=0x2AAA;
    assert(Invoke(state,stack,(uintptr_t)customImage)==0);
    assert(*(uint64_t*)(g_base+kElements+408*3+kElementImage)==0x2AAA);
    assert(nativeCalls==0 && whiteLookups==102);

    // A stale element generation is rejected without writing or forwarding.
    g_pictures[0].image=(uintptr_t)customImage;
    *(uint8_t*)(customImage+kSlotInUse)=1;
    std::strcpy((char*)(customImage+kSlotName),"custom");
    whiteAvailable=true;
    *(uint16_t*)(handle+2)=8; // The UI element was recycled after this callback was queued.
    *(uint64_t*)(g_base+kElements+408*3+kElementImage)=0x3333;
    assert(Invoke(state,stack,(uintptr_t)customImage)==0);
    assert(*(uint64_t*)(g_base+kElements+408*3+kElementImage)==0x3333);
    assert(nativeCalls==0 && whiteLookups==102);

    // Stock images retain the exact original arguments and native result.
    assert(Invoke(state,stack,(uintptr_t)stockImage)==0xC0FFEE);
    assert(nativeCalls==1);
    puts("PASS: live custom image, retired-slot white fallback, stale element generation and stock passthrough");
}
'''


def main():
    assert "StillOurs(*picture)" in SET_IMAGE
    assert 'g_findAsset(kImageType, "$white", 1, 0)' in SET_IMAGE
    assert "return 0;" in SET_IMAGE
    with tempfile.TemporaryDirectory(prefix="bo3-image-lifetime-") as temp:
        temp = Path(temp)
        source = temp / "image_lifetime.cpp"
        binary = temp / "image_lifetime"
        source.write_text(PREFIX + PICTURE_LOOKUP + "\n" + STILL_OURS + "\n" +
                          ELEMENT_ARGUMENT + "\n" + SET_IMAGE + "\n" + MAIN)
        subprocess.run([
            "g++", "-std=c++20", "-Wall", "-Wextra", "-Werror", "-O1",
            "-fsanitize=address,undefined", str(source), "-o", str(binary)
        ], check=True)
        subprocess.run([str(binary)], check=True)


if __name__ == "__main__":
    main()
