"""智估价 AI — FastAPI 后端入口。"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from workflow.orchestrator import Orchestrator
from skills.chat import ChatSkill

app = FastAPI(title="智估价 AI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = Orchestrator()


class ValuateParams(BaseModel):
    city: str = ""
    district: str = ""
    keyword: str = ""
    area: float = 100
    houseCount: int = 0


class ValuateRequest(BaseModel):
    query: str = ""
    params: ValuateParams = ValuateParams()


@app.get("/")
async def root():
    return {"service": "智估价 AI API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "ok"}


chat_skill = ChatSkill()


@app.post("/api/valuate")
async def valuate(req: ValuateRequest):
    p = req.params
    result = await orchestrator.run(
        city=p.city,
        district=p.district,
        keyword=p.keyword,
        area=p.area,
        house_count=p.houseCount,
        query=req.query,
    )
    return result


class ChatRequest(BaseModel):
    message: str


@app.post("/api/chat")
async def chat(req: ChatRequest):
    result = await chat_skill.execute({"message": req.message})
    return result
