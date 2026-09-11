from fastapi import FastAPI

app = FastAPI(title="BotForge Arena")


@app.get("/health")
def health():
    return {"status": "ok"}
