from worker.celery_client import client


def commiter():
    client.send_task("commiter")
    print("✅ Commiter Task 1 sent to CloudAMQP task is commiter")


def extract_transaction_from_telegram( 
        chat_id: int,
        caption: str,   
        file_id: str,
        bot_token: str,
        gemini_api_key: str,
        platform: str):
    client.send_task("extract_transaction_from_telegram",
                        args=[chat_id, caption, file_id, bot_token, gemini_api_key, platform])
    
    print("✅ transaction Task 1 sent to CloudAMQP task is  == extract_transaction_from_telegram")