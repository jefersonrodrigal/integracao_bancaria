# Fixtures de teste

Todos os arquivos e construtores deste diretório são **SINTÉTICOS**. Foram montados a partir
das posições do manual Itaú CNAB 400 (JANEIRO 2017) e **não** são arquivos oficiais do Itaú.

* `builders.py`: monta linhas de remessa e retorno com posições digitadas do manual, sem
  reutilizar os leiautes de `app/`.
* `golden/itau_cnab400_remessa_sintetica.rem`: saída de `builders.remittance_golden()`. O
  adaptador precisa reproduzi-la byte a byte.

Arquivos reais obtidos na homologação devem ser anonimizados e colocados em `oficial/`, com a
origem registrada.
