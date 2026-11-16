import json, os, time, boto3

sqs = boto3.client(
    "sqs", endpoint_url="http://localhost:9324", region_name="us-east-1",
    aws_access_key_id="x", aws_secret_access_key="x")
url = sqs.get_queue_url(QueueName="guias")["QueueUrl"]

def processar(pedido):
    if "requisicaoId" not in pedido:
        raise ValueError("mensagem sem requisicaoId")
    print(os.getpid(), "guia G-" + pedido["requisicaoId"], pedido.get("hospital"))
    time.sleep(0.5)

while True:
    resp = sqs.receive_message(
        QueueUrl=url, MaxNumberOfMessages=1, WaitTimeSeconds=10,
        MessageSystemAttributeNames=["ApproximateReceiveCount"])
    for m in resp.get("Messages", []):
        try:
            processar(json.loads(m["Body"]))
            sqs.delete_message(QueueUrl=url, ReceiptHandle=m["ReceiptHandle"])
        except Exception as e:
            print("falhou; volta para a fila:", e, m.get("Attributes"))