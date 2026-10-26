#include "continuity.hpp"
#include <iostream>
#include <filesystem>
#include <cstdlib>
#include <string>
#include <fstream>
#include <stdexcept>

static std::string file_sha(const std::string& path) {
  if(path.empty())return "";
  std::ifstream f(path,std::ios::binary);if(!f)throw std::runtime_error("cannot read output for hash");
  SHA256_CTX ctx;SHA256_Init(&ctx);char buf[65536];
  while(f){f.read(buf,sizeof(buf));std::streamsize n=f.gcount();if(n)SHA256_Update(&ctx,buf,static_cast<size_t>(n));}
  unsigned char dig[SHA256_DIGEST_LENGTH];SHA256_Final(dig,&ctx);
  constexpr char hex[]="0123456789abcdef";std::string out;
  for(unsigned char v:dig){out+=hex[v>>4];out+=hex[v&15];}return out;
}
int main(int argc,char**argv) {
  try {
    std::string arm="adaptive_damage",snapshot="",resume="",observer="",receipt="";
    uint64_t seed=17,target=1000,checkpoint_every=1000,observer_every=100;
    int max_rounds=45,damage_interval=50000;
    for(int i=1;i<argc;i++){
      std::string key=argv[i];if(i+1>=argc)throw std::invalid_argument("missing value for "+key);
      std::string value=argv[++i];
      if(key=="--arm")arm=value;
      else if(key=="--seed")seed=std::stoull(value);
      else if(key=="--target-episodes")target=std::stoull(value);
      else if(key=="--damage-interval")damage_interval=std::stoi(value);
      else if(key=="--max-rounds")max_rounds=std::stoi(value);
      else if(key=="--checkpoint-every")checkpoint_every=std::stoull(value);
      else if(key=="--snapshot")snapshot=value;
      else if(key=="--resume")resume=value;
      else if(key=="--observer-log")observer=value;
      else if(key=="--observe-every")observer_every=std::stoull(value);
      else if(key=="--receipt")receipt=value;
      else throw std::invalid_argument("unknown option "+key);
    }
    auto summary=triad::simulate_continuous(seed,arm,target,max_rounds,damage_interval,
                             checkpoint_every,snapshot,observer,observer_every,resume);
    std::string out="{\"schema\":\"are-selfmodel-continuity-receipt-1\",\"summary\":"+summary.to_json()
                   +",\"snapshot_sha256\":\""+file_sha(snapshot)+"\",\"observer_sha256\":\""+file_sha(observer)+"\"}\\n";
    // Emit actual JSON newline, not escaped characters in the receipt file.
    out[out.size()-2]='\n';out.pop_back();
    if(!receipt.empty()){
      std::ofstream f(receipt,std::ios::out|std::ios::trunc);
      if(!f)throw std::runtime_error("cannot write receipt");f<<out;
    } else std::cout<<out;
    std::cerr<<"CONTINUITY_OK arm="<<arm<<" target="<<target<<" seconds="<<summary.elapsed_seconds
             <<" event_digest="<<summary.event_rolling_sha256<<"\n";
    return 0;
  }catch(const std::exception& e){std::cerr<<"ERROR "<<e.what()<<"\n";return 2;}
}
