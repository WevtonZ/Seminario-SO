#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <fstream>
using namespace std;

string aux = "__aux_tmp__";
string file = "metricas.txt";
string csv = "metricas.csv";

vector<string> get_inputs(){
    vector<string> inputs;

    string cmd = "ls inputs/ > " + aux;
    system(cmd.c_str());

    ifstream st;
    st.open(aux);
    string s;
    while(st >> s){
        inputs.push_back(s);
    }
    st.close();
    return inputs;
}

int main(){
    system("g++ prog.cpp -o prog");
    
    auto inputs = get_inputs();
    ofstream output;
    output.open(csv);

    output << "Tempo Total de Execução, Tempo de CPU, Utilização Média de CPU, Pico de Memória Residente\n";
    for(auto in: inputs){
        cout<<"Processando: "<<in<<endl;
        string path  = "inputs/"+in;
        string cmd = "/usr/bin/time -f '%e %U %S %P %M' -o " + file + " ./prog < " + path + " > " + aux;

        system(cmd.c_str());


        ifstream st;
        st.open(file);

        //tempo total ,	Tempo de CPU em modo usuário , 	Tempo de CPU em modo kernel , 	Utilização média de CPU , 	Pico de memória residente em KiB
        // 0.00 0.00 0.00 66% 4120
        long double tempo_total, tempo_cpu_usuario, tempo_cpu_kernel;
        string media_cpu;
        int memoria;

        st >> tempo_total >> tempo_cpu_usuario >> tempo_cpu_kernel >> media_cpu >> memoria;
        long double tempo_cpu = tempo_cpu_usuario + tempo_cpu_kernel;

        output << tempo_total << ", " << tempo_cpu << ", " << media_cpu <<", "<< memoria << "\n";
 
        st.close();
    }
    output.close();

    for(string s: {aux, file}) {
        string cmd = "rm " + s;
        system(cmd.c_str());
    }

    return 0;
}
