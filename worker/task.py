from worker.celery_client import client


def commiter():
    client.send_task("commiter")
    print("✅ Commiter Task 1 sent to CloudAMQP (Instant)")


commiter()