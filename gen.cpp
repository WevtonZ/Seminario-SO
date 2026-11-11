#include <bits/stdc++.h>
using namespace std;

mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

void gen(int n){
    int k = 10;
    int pot = log10(n);
    int lim = 1e9;

    for(int i = 1; i <= k; i++){
        string file = "inputs/in_1e"+to_string(pot)+"_"+to_string(i);
        ofstream output;
        output.open(file);
        output<<n<<'\n';
        for(int i=1;i<=n;i++){
            output << rng() % lim << ' ';
        }
        output << '\n';
        output.close();
    }
}

int main(){
    ios::sync_with_stdio(0);
    cin.tie(0);

    system("mkdir inputs");
    for(int n = 1e3; n <= int(1e7); n *= 10) gen(n);

    return 0;
}