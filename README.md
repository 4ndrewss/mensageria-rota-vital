# 📬 Atividade 2: Mensageria

Infraestrutura de Software · ADS · CESAR School · 2026.2

Uma fila compatível com o Amazon SQS, um produtor e dois consumidores, rodando no meu computador. Cada mensagem é um pedido de hospital do Rota Vital, e o consumidor gera a guia de transporte (só imprime na tela).

<!-- ## 🎥 Vídeo -->

<!-- [Assistir no YouTube](COLE_O_LINK_AQUI) -->

## 🛤️ Caminho escolhido

**Caminho A:** ElasticMQ local em Docker, sem conta em provedor e sem cartão.

## ▶️ Como rodar

Pré-requisitos: Docker Desktop, AWS CLI v2, Python 3.12+ e `pip install boto3`.

1. Subir a fila (deixar este terminal aberto):
   ```
   docker compose up
   ```
2. Em outro terminal, criar a fila `guias` com visibility timeout de 15 segundos (PowerShell):
   ```
   $env:AWS_ACCESS_KEY_ID="x"; $env:AWS_SECRET_ACCESS_KEY="x"; $env:AWS_DEFAULT_REGION="us-east-1"
   aws sqs create-queue --queue-name guias --attributes VisibilityTimeout=15 --endpoint-url http://localhost:9324
   ```
3. Abrir dois terminais e rodar o consumidor em cada um:
   ```
   python consumidor.py
   ```
4. Em outro terminal, rodar o produtor (publica 20 pedidos válidos e 1 inválido):
   ```
   python produtor.py
   ```

## 📁 Arquivos

- [`docker-compose.yml`](./docker-compose.yaml): sobe o ElasticMQ na porta 9324
- [`produtor.py`](./produtor.py): envia 20 pedidos válidos e 1 sem `requisicaoId`
- [`consumidor.py`](./consumidor.py): recebe, processa e só então apaga a mensagem
- [`evidencias/`](./evidencias/): prints dos comandos e das saídas

## 🔧 Mudanças no código do PDF

No [`consumidor.py`](./consumidor.py) troquei `MaxNumberOfMessages=10` por `1` e adicionei `time.sleep(0.5)` em `processar`. Sem isso, um consumidor pega quase todas as mensagens de uma vez e o outro fica sem nada, e a divisão do trabalho não aparece.

## 📸 Evidências

| Arquivo | O que mostra |
|---|---|
| [`01-fila-criada.png`](./evidencias/01-fila-criada.png) | Fila `guias` criada com a `QueueUrl` |
| [`02-produtor-enviou-21.png`](./evidencias/02-produtor-enviou-21.png) | Produtor enviando as 21 mensagens |
| [`03-consumidor-guias-e-invalida.png`](./evidencias/03-consumidor-guias-e-invalida.png) | Um consumidor gerando as 20 guias e a inválida voltando, com `ApproximateReceiveCount` subindo |
| [`04-dois-consumidores.png`](./evidencias/04-dois-consumidores.png) | Dois consumidores (PIDs 21076 e 20588) dividindo as mensagens |

## ❓ Perguntas

### 1. Por que o consumidor só apaga a mensagem depois de processar? O que aconteceria se apagasse antes?

---

O consumidor só apaga **depois de processar** porque apagar é a **confirmação de que deu certo**. Enquanto não apaga, a fila continua com a mensagem e **devolve ela depois do visibility timeout**. Foi o que vi com a mensagem inválida: o processamento deu erro, ela **não foi apagada** e ficou voltando a cada 15 segundos, até eu parar o programa com `Ctrl+C`.

Se apagasse **antes** de processar e o consumidor falhasse no meio (erro ou queda), a mensagem estaria **perdida**: a fila já a teria descartado e ninguém geraria a guia. Esse pedido **sumiria sem deixar rastro**.

### 2. Com dois consumidores, como as mensagens se dividiram? A ordem foi mantida? O que a documentação do SQS diz sobre ordem nas filas padrão?

---

Rodei dois consumidores ao mesmo tempo (PIDs `21076` e `20588`) e depois o produtor. As mensagens se **dividiram quase igual**: o consumidor A (`21076`) pegou as guias R-001, 003, 005, 007, 009, 011, 013, 015, 017 e 019, e o consumidor B (`20588`) pegou as R-002, 004, 006, 008, 010, 012, 014, 016, 018 e 020. Cada mensagem foi entregue a **um só consumidor**, então o trabalho foi dividido (nenhuma guia foi gerada duas vezes). A mensagem inválida também foi recebida pelos dois, e o contador de recebimentos subiu de forma **compartilhada** (1, 2, 3... entre os dois terminais), porque a contagem é da mensagem na fila, não de cada consumidor.

Quanto à ordem, dentro de cada consumidor ela foi mantida (cada um recebeu os números em ordem crescente), e juntando os dois a sequência também saiu certinha. Mas isso **não é garantido**. A documentação do SQS diz que a fila padrão tem ordenação **"de melhor esforço"**: as mensagens geralmente chegam na ordem em que foram enviadas, mas a ordem **pode mudar**. Na minha execução ela ficou organizada porque as mensagens eram poucas, cada consumidor pegava uma de cada vez (`MaxNumberOfMessages=1`) e eu coloquei uma pausa de 0,5 segundo. Se a ordem for importante, é preciso usar uma **fila FIFO**, ou o consumidor não pode depender dela.

### 3. A fila padrão garante entrega pelo menos uma vez, e a mesma mensagem pode chegar duas vezes. O que isso exige do consumidor? Como vocês o tornariam idempotente?

---

Isso exige que o consumidor **aguente receber a mesma mensagem mais de uma vez** sem causar problema. Não é um bug da fila: ela garante que a mensagem chega **pelo menos uma vez**, e por isso uma **duplicata** pode acontecer (por exemplo, se o consumidor processa mas cai antes de apagar).

Para tornar o consumidor **idempotente** (processar duas vezes dá o mesmo resultado de processar uma), eu guardaria os `requisicaoId` **já processados** (em um conjunto na memória ou, melhor, em um banco). Ao receber uma mensagem, o consumidor confere: se o ID **já está lá**, só apaga a mensagem e **não gera a guia de novo**. Assim cada requisição tem **uma única guia**, mesmo com mensagens repetidas.

### 4. Expliquem o visibility timeout com o que viram na mensagem inválida. Para que serve uma DLQ?

---

O **visibility timeout** é o tempo que uma mensagem fica **invisível para os outros consumidores** depois que alguém a recebe. Nesse tempo, o consumidor tem que processar e apagar. Se não apagar, a mensagem **volta para a fila**. Na minha fila o valor era de **15 segundos**: a mensagem inválida (sem `requisicaoId`) deu erro, não foi apagada e **reapareceu a cada 15 segundos**, com o `ApproximateReceiveCount` subindo (1, 2, 3...).

A **DLQ** (fila de mensagens mortas) é uma **fila separada** para onde a mensagem vai depois de falhar um número de vezes (o `maxReceiveCount`, por exemplo 3). Serve para a mensagem com problema **parar de ficar voltando** e atrapalhando a fila principal, e para eu poder **analisar o erro depois** com calma. Neste trabalho não configurei a DLQ (é opcional); a mensagem inválida ficou voltando até eu parar o consumidor.

### 5. No Rota Vital, qual a diferença entre o hospital chamar a emissão de guia diretamente (síncrono) e passar por uma fila (assíncrono)? O que se ganha e o que se perde?

---

No modo **síncrono**, o hospital chama a emissão da guia e **fica esperando** a resposta. Se o serviço de guias estiver lento ou fora do ar, o hospital **fica travado** ou recebe erro. Em compensação, ele **já sabe na hora** se a guia foi gerada.

No modo **assíncrono**, o hospital só coloca o pedido na fila e **segue com o trabalho**, e os consumidores geram as guias no ritmo deles. **Ganha-se:** o hospital não fica esperando, a fila aguenta muitos pedidos de uma vez e, se um consumidor falhar, o pedido volta e é tentado de novo. **Perde-se:** a resposta imediata (o hospital não sabe na hora se a guia saiu), a ordem pode mudar e pode haver mensagens duplicadas, então é preciso cuidar disso no consumidor.

## 🤖 Uso de IA

- **Ferramenta:** Claude (Anthropic).
- **Finalidade:** apoio para entender o enunciado, resolver erros de instalação e de comandos no Windows (AWS CLI e PowerShell), organizar a estrutura do repositório, das evidências e do README, e revisar o texto das respostas.
- **Como validei:** executei todos os comandos e o código na minha máquina e conferi as saídas com os prints em [`evidencias/`](./evidencias/). As observações da pergunta 2 (PIDs e divisão das guias) vêm da minha própria execução. Conferi o comportamento de ordem das filas padrão e do visibility timeout na documentação do SQS indicada no enunciado. Sei explicar o código e o que cada parte faz.
