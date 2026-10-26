#include "continuity.hpp"
#include <cassert>
#include <iostream>
int main(){
    using namespace triad;
    Brain a(2,17,true,true,true,15);a.dynamic_memory=true;
    auto before=a.observe(INITIAL_HP,0);
    a.on_help(0,2);auto after=a.observe(INITIAL_HP,0);
    assert(after[3]>before[3]);
    for(int t=0;t<30;t++)a.on_help(0,2);
    double peak=a.observe(INITIAL_HP,0)[3];
    for(int t=0;t<100;t++)a.on_result(-1,50);
    assert(a.observe(INITIAL_HP,0)[3]<peak);
    assert(a.helped_by[0]==31);
    assert(a.observe(INITIAL_HP,0)[3]>0);
    Brain original(2,17,true,true,true,15);
    for(int t=0;t<30;t++)original.on_help(0,2);
    assert(original.observe(INITIAL_HP,0)[3]==1.);
    std::cout<<"PASS dynamic social memory decays while audit counts persist\n";
}
