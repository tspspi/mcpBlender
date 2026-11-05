// Independent fixture encoding through the installed OpenEXR C++ library.
#include <OpenEXR/ImfChannelList.h>
#include <OpenEXR/ImfFrameBuffer.h>
#include <OpenEXR/ImfHeader.h>
#include <OpenEXR/ImfOutputFile.h>
#include <OpenEXR/ImfMultiPartOutputFile.h>
#include <OpenEXR/ImfOutputPart.h>
#include <OpenEXR/ImfPartType.h>
#include <filesystem>
#include <string>
#include <vector>
using namespace OPENEXR_IMF_NAMESPACE;
int main(int argc,char** argv) {
    if (argc!=2) return 1;
    const int w=35,h=19;
    std::vector<std::vector<float>> pixels(8,std::vector<float>(w*h));
    for(int c=0;c<8;++c) for(int y=0;y<h;++y) for(int x=0;x<w;++x)
        pixels[c][y*w+x]=float((x*17+y*31+c*43)%101-50)/8.f;
    const Compression codecs[]={NO_COMPRESSION,ZIPS_COMPRESSION,ZIP_COMPRESSION};
    for(int mode=0;mode<3;++mode) for(int multi=0;multi<2;++multi) for(int order=0;order<2;++order) {
        std::vector<Header> headers;std::vector<FrameBuffer> frames;
        int index=0;
        for(int part=0;part<(multi?3:1);++part) {
            Header header(w,h);header.compression()=codecs[mode];header.lineOrder()=order?DECREASING_Y:INCREASING_Y;
            header.dataWindow()=IMATH_NAMESPACE::Box2i(IMATH_NAMESPACE::V2i(-3,-2),IMATH_NAMESPACE::V2i(w-4,h-3));
            if(multi) {header.setName("part"+std::to_string(part));header.setType(SCANLINEIMAGE);}
            FrameBuffer frame;int channels=multi?(part==0?4:part==1?1:3):8;
            for(int i=0;i<channels;++i,++index) {
                std::string name="field"+std::to_string(index);
                header.channels().insert(name,Channel(FLOAT));
                char* base=reinterpret_cast<char*>(pixels[index].data())+(3+2*w)*sizeof(float);
                frame.insert(name,Slice(FLOAT,base,sizeof(float),w*sizeof(float)));
            }
            headers.push_back(header);frames.push_back(frame);
        }
        std::string file=std::string(argv[1])+"/fixture-"+std::to_string(mode)+"-"+std::to_string(multi)+(order?"-decreasing":"")+".exr";
        if(multi) {
            MultiPartOutputFile out(file.c_str(),headers.data(),int(headers.size()));
            for(int i=0;i<3;++i) {OutputPart part(out,i);part.setFrameBuffer(frames[i]);part.writePixels(h);}
        } else {OutputFile out(file.c_str(),headers[0]);out.setFrameBuffer(frames[0]);out.writePixels(h);}
    }
    // Exercise the exact multipart boundary independently of Python parsing.
    for(int count : {31,32,33}) {
        std::vector<Header> headers;
        for(int i=0;i<count;++i) {
            Header header(1,1);header.setName("part"+std::to_string(i));
            header.setType(SCANLINEIMAGE);header.compression()=NO_COMPRESSION;
            header.channels().insert("field"+std::to_string(i),Channel(FLOAT));
            headers.push_back(header);
        }
        std::string file=std::string(argv[1])+"/parts-"+std::to_string(count)+".exr";
        MultiPartOutputFile out(file.c_str(),headers.data(),count);
        for(int i=0;i<count;++i) {
            float value=float(i)-16.5f;FrameBuffer frame;
            frame.insert("field"+std::to_string(i),Slice(FLOAT,reinterpret_cast<char*>(&value),sizeof(float),sizeof(float)));
            OutputPart part(out,i);part.setFrameBuffer(frame);part.writePixels(1);
        }
    }
    return 0;
}
