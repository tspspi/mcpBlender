// Independent scene-linear HDR/alpha fixtures through installed OpenEXR.
#include <OpenEXR/ImfChannelList.h>
#include <OpenEXR/ImfFrameBuffer.h>
#include <OpenEXR/ImfHeader.h>
#include <OpenEXR/ImfOutputFile.h>
#include <limits>
#include <cmath>
#include <string>
#include <vector>
using namespace OPENEXR_IMF_NAMESPACE;
int main(int argc,char** argv) {
    if(argc!=2) return 1;
    for(const std::string mode:{"premult","straight","bright","black","negative","nan","bad-alpha","offset","bare","wrong-size"}) {
        int w=mode=="wrong-size"?4:5,h=3;
        Header header(w,h);header.compression()=ZIP_COMPRESSION;
        bool offset=mode=="offset";
        if(offset) header.dataWindow()=IMATH_NAMESPACE::Box2i(IMATH_NAMESPACE::V2i(-3,-2),IMATH_NAMESPACE::V2i(w-4,h-3));
        std::vector<std::vector<float>> pixels(8,std::vector<float>(w*h));
        for(int y=0;y<h;++y) for(int x=0;x<w;++x) {
            float alpha=x/4.f;float rgb[]={4.f+y*.5f+x*.25f,2.f,-.25f};
            for(int c=0;c<3;++c) {
                float value=rgb[c]*(mode=="bright"?2.f:1.f);
                if(mode=="black") value=0.f;
                if(mode=="negative") value=-std::abs(value);
                pixels[c][y*w+x]=value*(mode=="straight"?1.f:alpha);
                pixels[c+4][y*w+x]=rgb[c]*alpha*5.f;
            }
            pixels[3][y*w+x]=pixels[7][y*w+x]=alpha;
        }
        if(mode=="nan") pixels[0][0]=std::numeric_limits<float>::quiet_NaN();
        if(mode=="bad-alpha") pixels[3][0]=1.1f;
        FrameBuffer frame;
        for(int c=0;c<8;++c) {
            std::string name=c<4?(mode=="bare"?"":"Layer.Combined."):"Other.Combined.";
            name+="RGBA"[c%4];header.channels().insert(name,Channel(FLOAT));
            char* base=reinterpret_cast<char*>(pixels[c].data())+(offset?(3+2*w)*sizeof(float):0);
            frame.insert(name,Slice(FLOAT,base,sizeof(float),w*sizeof(float)));
        }
        std::string path=std::string(argv[1])+"/"+mode+".exr";
        OutputFile file(path.c_str(),header);file.setFrameBuffer(frame);file.writePixels(h);
    }
}
