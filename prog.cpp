#include <vector>
#include <iostream>
#include <algorithm>
using namespace std;
int main(){
    #ifdef FASTIO
    ios::sync_with_stdio(0);
    cin.tie(0);
    #endif

    int n; cin >> n;
    vector<int>v(n);
    for(int&x:v)cin>>x;
    #ifdef SORT
    sort(v.begin(),v.end());
    #endif
    for(int&x:v)cout<<x<<' ';
    cout<<'\n';

    return 0;
}
