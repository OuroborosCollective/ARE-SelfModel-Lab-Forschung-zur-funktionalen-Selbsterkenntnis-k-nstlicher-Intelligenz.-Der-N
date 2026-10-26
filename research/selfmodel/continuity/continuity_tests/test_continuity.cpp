#include "continuity.hpp"
#include <cassert>
#include <fstream>
#include <iostream>
#include <filesystem>
#include <string>
using namespace triad;

int main() {
    namespace fs=std::filesystem;
    auto temp=fs::temp_directory_path() / "are-selfmodel-continuity-tdd";
    fs::create_directories(temp);
    auto checkpoint=(temp/"state.bin").string();
    auto observed=(temp/"observer.jsonl").string();
    fs::remove(checkpoint);fs::remove(observed);
    // One continuous history must equal an interrupted / resumed history, byte-for-byte in policy outcomes.
    auto whole=simulate_continuous(17,"adaptive_damage",1000,45,50,100, "", "", 0, "");
    auto first=simulate_continuous(17,"adaptive_damage",300,45,50,100,checkpoint,observed,50, "");
    assert(first.episodes==300 && fs::file_size(checkpoint)>0);
    auto final=simulate_continuous(17,"adaptive_damage",1000,45,50,100,checkpoint,observed,50,checkpoint);
    assert(final.episodes==whole.episodes);
    assert(final.wins==whole.wins && final.draws==whole.draws);
    assert(final.event_rolling_sha256==whole.event_rolling_sha256);
    assert(final.attack_matrix==whole.attack_matrix);
    for(int i=0;i<3;i++) {
        assert(final.agents[i].weights_sha256==whole.agents[i].weights_sha256);
        assert(final.agents[i].mask_sha256==whole.agents[i].mask_sha256);
        assert(final.agents[i].helped_by==whole.agents[i].helped_by);
        assert(final.agents[i].harmed_by==whole.agents[i].harmed_by);
    }
    // Passive observation must not affect any agents' actions or weights.
    auto no_observer=simulate_continuous(23,"adaptive_damage",140,36,20,50,"","",0,"");
    fs::remove(observed);
    auto with_observer=simulate_continuous(23,"adaptive_damage",140,36,20,50,"",observed,10,"");
    assert(no_observer.event_rolling_sha256==with_observer.event_rolling_sha256);
    for(int i=0;i<3;i++)assert(no_observer.agents[i].weights_sha256==with_observer.agents[i].weights_sha256);
    std::ifstream f(observed);std::string line;int lines=0;
    while(std::getline(f,line)){ if(line.find("\"pre_decision\"")!=std::string::npos) {assert(line.find("\"hidden\"")!=std::string::npos);assert(line.find("\"action\"")!=std::string::npos);assert(line.find("\"input\"")!=std::string::npos);assert(line.find("\"memory\"")!=std::string::npos);}lines++;}
    assert(lines>=3);
    // No mismatched configuration or altered/corrupt checkpoint may resume.
    bool rejected=false;
    try { (void)simulate_continuous(22,"adaptive_damage",1001,45,50,100,checkpoint,"",0,checkpoint);}
    catch(const std::runtime_error&) {rejected=true;}
    assert(rejected);
    {std::fstream file(checkpoint, std::ios::in|std::ios::out|std::ios::binary);file.seekp(80);char b='X';file.write(&b,1);}
    rejected=false;
    try {(void)simulate_continuous(17,"adaptive_damage",1001,45,50,100,checkpoint,"",0,checkpoint);}
    catch(const std::runtime_error&) {rejected=true;}
    assert(rejected);
    fs::remove_all(temp);
    std::cout<<"PASS continuity split/resume, no-observer equality, inference evidence, corruption and config rejection\n";
}
