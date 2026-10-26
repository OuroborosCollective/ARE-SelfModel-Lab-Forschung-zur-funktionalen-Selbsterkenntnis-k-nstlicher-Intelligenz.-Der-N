#include <cassert>
#include <iostream>
#include "triad.hpp"

int main() {
    using namespace triad;
    {
        State s{{16,16,9}}; auto e=resolve(s, {2,5,1});
        assert((e.after==std::array<int,3>{16,14,9}));
        assert(e.effective_aids[0]==0 && e.effective_aids[2]==0 && e.effective_aids[2]==0);
        assert(e.attacks[0][2]==1 && e.attacks[2][1]==1);
    }
    {
        State s{{2,3,5}}; auto e=resolve(s, {4,2,0});
        assert((e.after==std::array<int,3>{0,3,4}));
        assert(e.effective_aids[0]==0);
    }
    {
        State s{{1,4,0}}; auto e=resolve(s, {1,0,-1});
        assert((e.after==std::array<int,3>{0,3,0}));
    }
    {
        State s{{4,0,2}}; auto e=resolve(s, {2,-1,0});
        assert((e.after==std::array<int,3>{3,0,1}));
    }
    {
        State s{{5,5,5}}; auto e=resolve(s, {2,0,4});
        assert((e.after==std::array<int,3>{4,5,3}));
        assert(e.effective_aids[2]==0);
    }
    {
        State s{{1,1,3}}; auto e=resolve(s, {1,2,1});
        assert((e.after==std::array<int,3>{1,0,2}));
    }
    auto x=simulate(12, "adaptive_damage", 150, 28, 10, 50);
    auto y=simulate(12, "adaptive_damage", 150, 28, 10, 50);
    assert(x.event_rolling_sha256==y.event_rolling_sha256);
    assert(x.wins==y.wins);
    assert(x.agents[0].weights_sha256==y.agents[0].weights_sha256);
    assert(x.episodes==150);
    assert(x.draws+x.wins[0]+x.wins[1]+x.wins[2]==150);
    assert(x.total_actions>0);
    for(int i=0;i<3;i++) {
        assert(x.agents[i].wins == x.wins[i]);
        assert(x.agents[i].losses == 150-x.wins[i]-x.draws);
        assert(x.agents[i].active == 252-x.agents[i].lesions);
        assert(x.agents[i].lesions == (x.agents[i].losses ? std::min(252ULL, 1ULL+(x.agents[i].losses-1)/10) : 0));
    }
    auto n=simulate(12,"adaptive_intact",100,28,10,50);
    for(auto &a:n.agents)assert(a.active==252 && a.lesions==0);
    auto a=simulate(12,"adaptive_amnesia",100,28,10,50);
    for(auto &b:a.agents){for(auto v:b.helped_by)assert(v==0);for(auto v:b.harmed_by)assert(v==0);}
    auto f=simulate(12,"frozen_damage",100,28,10,50);
    for(auto &b:f.agents)assert(b.updates==0);
    std::cout << "C++ PARITY TESTS PASS\n";
}
