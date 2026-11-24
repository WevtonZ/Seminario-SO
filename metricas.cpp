#include <iostream>
#include <vector>
#include <string>
#include <fstream>
#include <cstdlib>
using namespace std;

const string aux = "__aux_tmp__", tfile = "metricas.txt", csv = "metricas.csv";

struct Variante { string nome, defs; };

int main(){
    vector<Variante> variantes = {
        {"rw_lento", ""}, {"rw_rapido", "-DFASTIO"},
        {"sort_lento", "-DSORT"}, {"sort_rapido", "-DSORT -DFASTIO"}};

    for(auto &v : variantes){
        string cmd = "g++ " + v.defs + " prog.cpp -o prog_" + v.nome;
        if(system(cmd.c_str()) != 0){ cerr << "falha ao compilar " << v.nome << "\n"; return 1; }
    }

    system(("ls inputs/ > " + aux).c_str());
    vector<string> inputs; { ifstream st(aux); string s; while(st >> s) inputs.push_back(s); }

    ofstream out(csv);
    out << "variante,arquivo,N,tempo_total,tempo_usuario,tempo_sistema,tempo_cpu,utilizacao_cpu,pico_memoria_kib\n";

    for(size_t i = 0; i < inputs.size(); i++){
        for(size_t k = 0; k < variantes.size(); k++){
            auto &v = variantes[(i + k) % variantes.size()];   // ordem das variantes gira a cada arquivo
            string path = "inputs/" + inputs[i];
            cout << "Processando: " << v.nome << " " << inputs[i] << endl;

            system("sync");                                    // grava a saída anterior antes de medir
            system(("cat " + path + " > /dev/null").c_str());  // entrada no cache, igual nos 3 ambientes
            string cmd = "/usr/bin/time -f '%e %U %S %P %M' -o " + tfile + " ./prog_" + v.nome
                       + " < " + path + " > " + aux;
            system(cmd.c_str());

            ifstream st(tfile);
            double total, usuario, sistema; string util; long mem;
            if(!(st >> total >> usuario >> sistema >> util >> mem)){ cerr << "leitura falhou\n"; continue; }
            out << v.nome << "," << inputs[i] << "," << inputs[i].substr(3, 3) << ","
                << total << "," << usuario << "," << sistema << "," << usuario + sistema << ","
                << util << "," << mem << "\n";
        }
    }
    out.close();
    system(("rm -f " + aux + " " + tfile).c_str());
    return 0;
}