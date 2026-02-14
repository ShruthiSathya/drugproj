from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import json

from models import QueryRequest, RepurposingResult
from pipeline.graph_builder import KnowledgeGraphBuilder
from pipeline.scorer import RepurposingScorer
from pipeline.llm_explainer import LLMExplainer
from pipeline.data_fetcher import DataFetcher

app = FastAPI(title="Drug Repurposing Engine", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

data_fetcher = DataFetcher()
graph_builder = KnowledgeGraphBuilder()
scorer = RepurposingScorer()
explainer = LLMExplainer()


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}


@app.post("/api/repurpose")
async def repurpose_drug(request: QueryRequest):
    try:
        disease_data = await data_fetcher.fetch_disease_data(request.disease_name)
        if not disease_data:
            raise HTTPException(status_code=404, detail=f"Could not find disease data for '{request.disease_name}'.")
        
        graph = graph_builder.build(disease_data)
        candidates = scorer.score_candidates(
            disease_data=disease_data, 
            graph=graph, 
            top_k=request.top_k, 
            min_score=request.min_score
        )
        
        # Enhanced: Add explanation about why we got these results
        print(f"Found {len(candidates)} candidates for {disease_data['name']}")
        for c in candidates[:3]:
            print(f"  - {c.drug_name}: score={c.composite_score:.2f}, shared_genes={len(c.shared_genes)}, shared_pathways={len(c.shared_pathways)}")
        
        candidates_with_explanations = await explainer.explain_candidates(
            disease_name=request.disease_name, 
            candidates=candidates, 
            api_key=request.anthropic_api_key
        )
        
        return RepurposingResult(
            disease_name=disease_data["name"],
            disease_genes=disease_data["genes"][:20],
            disease_pathways=disease_data["pathways"][:10],
            candidates=candidates_with_explanations,
            graph_stats=graph_builder.get_stats(graph),
            data_sources=["DisGeNET", "OpenTargets", "DrugBank", "KEGG", "UniProt"]
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/repurpose/stream")
async def repurpose_stream(request: QueryRequest):
    async def event_generator():
        try:
            yield f"data: {json.dumps({'stage': 'fetching', 'message': f'Fetching disease data for {request.disease_name}...'})}\n\n"
            
            disease_data = await data_fetcher.fetch_disease_data(request.disease_name)
            if not disease_data:
                yield f"data: {json.dumps({'stage': 'error', 'message': f'Disease \"{request.disease_name}\" not found. Try: Parkinson, Alzheimer, ALS, Lupus, Breast Cancer'})}\n\n"
                return
            
            yield f"data: {json.dumps({'stage': 'disease_found', 'data': {'name': disease_data['name'], 'gene_count': len(disease_data['genes']), 'pathway_count': len(disease_data['pathways'])}})}\n\n"
            
            yield f"data: {json.dumps({'stage': 'graph_building', 'message': 'Building knowledge graph...'})}\n\n"
            graph = graph_builder.build(disease_data)
            stats = graph_builder.get_stats(graph)
            yield f"data: {json.dumps({'stage': 'graph_built', 'data': stats})}\n\n"
            
            yield f"data: {json.dumps({'stage': 'scoring', 'message': 'Scoring drug candidates...'})}\n\n"
            candidates = scorer.score_candidates(
                disease_data=disease_data, 
                graph=graph, 
                top_k=request.top_k, 
                min_score=request.min_score
            )
            
            yield f"data: {json.dumps({'stage': 'scored', 'message': f'Found {len(candidates)} candidates'})}\n\n"
            
            if len(candidates) == 0:
                yield f"data: {json.dumps({'stage': 'warning', 'message': f'No candidates found with min_score={request.min_score}. Try lowering the minimum score.'})}\n\n"
            
            yield f"data: {json.dumps({'stage': 'explaining', 'message': 'Generating AI explanations...'})}\n\n"
            candidates_with_explanations = await explainer.explain_candidates(
                disease_name=request.disease_name, 
                candidates=candidates, 
                api_key=request.anthropic_api_key
            )
            
            result = {
                "stage": "complete",
                "data": {
                    "disease_name": disease_data["name"],
                    "disease_genes": disease_data["genes"][:20],
                    "disease_pathways": disease_data["pathways"][:10],
                    "candidates": [c.model_dump() for c in candidates_with_explanations],
                    "graph_stats": stats,
                    "data_sources": ["DisGeNET", "OpenTargets", "DrugBank", "KEGG", "UniProt"]
                }
            }
            yield f"data: {json.dumps(result)}\n\n"
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'stage': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")