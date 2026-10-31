import json
import logging
from typing import List, Dict, Any, Tuple
from uuid import UUID
import re

from app.schemas.decision import (
    DecisionFactor, DecisionConflict, DecisionRisk, DecisionImpact, DecisionAlternative,
    MatrixScore
)
from app.llm.provider import ChatMessage
from app.services.rag.generator import rag_generator

logger = logging.getLogger(__name__)

def parse_json_from_llm(res: Any) -> Dict[str, Any]:
    if not res or not isinstance(res, str):
        return {}
    match = re.search(r'\{.*\}', res, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except:
            pass
    
    # Try finding an array if it's a list response
    match = re.search(r'\[.*\]', res, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except:
            pass
            
    try:
        return json.loads(res)
    except:
        return {}

class Analyzers:
    def __init__(self):
        self.llm_provider = rag_generator.llm_provider

    async def detect_conflicts(self, context_text: str) -> List[DecisionConflict]:
        prompt = f"""Analyze the provided evidence for any contradictions or conflicting claims between different sources.
Return ONLY valid JSON in this exact format:
{{"conflicts": [{{"claim_a": "...", "source_a": "1", "claim_b": "...", "source_b": "2", "unresolved": true}}]}}
If no conflicts exist, return: {{"conflicts": []}}

Evidence:
{context_text}"""
        res = await self.llm_provider.generate_response([ChatMessage(role="user", content=prompt)])
        data = parse_json_from_llm(res)
        conflicts = []
        for c in data.get("conflicts", []):
            conflicts.append(DecisionConflict(
                claim_a=c.get("claim_a", ""),
                source_a=str(c.get("source_a", "")),
                claim_b=c.get("claim_b", ""),
                source_b=str(c.get("source_b", "")),
                unresolved=c.get("unresolved", True)
            ))
        return conflicts

    async def extract_factors(self, query: str, context_text: str) -> List[DecisionFactor]:
        prompt = f"""Extract key decision factors (pros, cons, features, requirements) relevant to this query: "{query}"
Rule: EVERY factor MUST be directly supported by the evidence and must cite the exact source ID.
Return ONLY valid JSON in this format:
{{"factors": [{{"description": "...", "source_id": "1", "evidence_snippet": "..."}}]}}

Evidence:
{context_text}"""
        res = await self.llm_provider.generate_response([ChatMessage(role="user", content=prompt)])
        data = parse_json_from_llm(res)
        factors = []
        for f in data.get("factors", []):
            factors.append(DecisionFactor(
                description=f.get("description", ""),
                source_id=str(f.get("source_id", "")),
                evidence_snippet=f.get("evidence_snippet", "")
            ))
        return factors

    async def analyze_comparison(self, query: str, context_text: str) -> Tuple[List[DecisionFactor], List[DecisionFactor], List[DecisionFactor], List[DecisionFactor]]:
        prompt = f"""Compare the options mentioned in this query: "{query}"
Rule: EVERY point MUST be directly supported by the evidence and must cite the exact source ID.
Return ONLY valid JSON in this format:
{{
  "similarities": [{{"description": "...", "source_id": "1", "evidence_snippet": "..."}}],
  "differences": [...],
  "advantages": [...],
  "disadvantages": [...]
}}

Evidence:
{context_text}"""
        res = await self.llm_provider.generate_response([ChatMessage(role="user", content=prompt)])
        data = parse_json_from_llm(res)
        
        def parse_factors(key):
            return [DecisionFactor(
                description=f.get("description", ""),
                source_id=str(f.get("source_id", "")),
                evidence_snippet=f.get("evidence_snippet", "")
            ) for f in data.get(key, [])]
            
        return parse_factors("similarities"), parse_factors("differences"), parse_factors("advantages"), parse_factors("disadvantages")

    async def analyze_recommendation(self, query: str, context_text: str) -> Tuple[str, str, List[DecisionAlternative]]:
        prompt = f"""Provide a recommendation for this query: "{query}"
Rule: Your recommendation MUST be strictly based on the evidence. Do NOT invent a recommendation if the evidence is insufficient.
Return ONLY valid JSON in this format:
{{
  "recommendation": "...",
  "reasoning": "...",
  "alternatives": [{{"name": "...", "description": "...", "source_id": "1", "evidence_snippet": "..."}}]
}}

Evidence:
{context_text}"""
        res = await self.llm_provider.generate_response([ChatMessage(role="user", content=prompt)])
        data = parse_json_from_llm(res)
        alts = [DecisionAlternative(
            name=a.get("name", ""),
            description=a.get("description", ""),
            source_id=str(a.get("source_id", "")),
            evidence_snippet=a.get("evidence_snippet", "")
        ) for a in data.get("alternatives", [])]
        
        return data.get("recommendation", "No recommendation possible."), data.get("reasoning", ""), alts

    async def analyze_risk(self, query: str, context_text: str) -> List[DecisionRisk]:
        prompt = f"""Analyze the risks for this query: "{query}"
Rule: EVERY risk MUST be directly supported by the evidence and must cite the exact source ID.
Return ONLY valid JSON in this format:
{{"risks": [{{"description": "...", "severity": "High/Medium/Low", "likelihood": "...", "mitigation": "...", "source_id": "1", "evidence_snippet": "..."}}]}}

Evidence:
{context_text}"""
        res = await self.llm_provider.generate_response([ChatMessage(role="user", content=prompt)])
        data = parse_json_from_llm(res)
        risks = []
        for r in data.get("risks", []):
            risks.append(DecisionRisk(
                description=r.get("description", ""),
                severity=r.get("severity", "Medium"),
                likelihood=r.get("likelihood", ""),
                mitigation=r.get("mitigation", ""),
                source_id=str(r.get("source_id", "")),
                evidence_snippet=r.get("evidence_snippet", "")
            ))
        return risks

    async def analyze_impact(self, query: str, context_text: str) -> Tuple[List[DecisionImpact], List[DecisionFactor]]:
        prompt = f"""Analyze the impacts and dependencies for this query: "{query}"
Rule: EVERY impact and dependency MUST be directly supported by the evidence.
Return ONLY valid JSON in this format:
{{
  "impacts": [{{"description": "...", "affected_area": "...", "source_id": "1", "evidence_snippet": "..."}}],
  "dependencies": [{{"description": "...", "source_id": "1", "evidence_snippet": "..."}}]
}}

Evidence:
{context_text}"""
        res = await self.llm_provider.generate_response([ChatMessage(role="user", content=prompt)])
        data = parse_json_from_llm(res)
        
        impacts = [DecisionImpact(
            description=i.get("description", ""),
            affected_area=i.get("affected_area", ""),
            source_id=str(i.get("source_id", "")),
            evidence_snippet=i.get("evidence_snippet", "")
        ) for i in data.get("impacts", [])]
        
        dependencies = [DecisionFactor(
            description=d.get("description", ""),
            source_id=str(d.get("source_id", "")),
            evidence_snippet=d.get("evidence_snippet", "")
        ) for d in data.get("dependencies", [])]
        
        return impacts, dependencies

    async def calculate_matrix(self, query: str, context_text: str) -> Tuple[List[Dict[str, Any]], List[MatrixScore], Dict[str, float]]:
        # 1. Ask LLM to extract criteria and categorical scores
        prompt = f"""Create a decision matrix for this query: "{query}"
Rule: Identify the options and criteria. Assess each option against each criterion using categories High, Medium, Low based ONLY on the evidence.
Return ONLY valid JSON in this format:
{{
  "criteria": [{{"name": "...", "weight": 0.5}}],
  "assessments": [{{"criterion": "...", "option": "...", "assessment": "High", "source_id": "1", "evidence_snippet": "..."}}]
}}
Make sure criteria weights sum to 1.0 roughly.

Evidence:
{context_text}"""
        res = await self.llm_provider.generate_response([ChatMessage(role="user", content=prompt)])
        data = parse_json_from_llm(res)
        
        criteria_data = data.get("criteria", [])
        
        # Weight validation & normalization
        valid_criteria = []
        total_weight = 0.0
        for c in criteria_data:
            w = float(c.get("weight", 1.0))
            if w < 0: w = 0
            total_weight += w
            
        for c in criteria_data:
            w = float(c.get("weight", 1.0))
            if w < 0: w = 0
            nw = w / total_weight if total_weight > 0 else 1.0
            valid_criteria.append({"name": c.get("name", "Unknown"), "weight": nw})
            
        criteria_dict = {c["name"]: c["weight"] for c in valid_criteria}
        
        # Scoring Math
        score_map = {"High": 3.0, "Medium": 2.0, "Low": 1.0}
        
        scores = []
        total_scores = {}
        for a in data.get("assessments", []):
            c_name = a.get("criterion", "")
            opt = a.get("option", "")
            assess = a.get("assessment", "Medium")
            n_score = score_map.get(assess, 2.0)
            weight = criteria_dict.get(c_name, 0.0)
            weighted_score = n_score * weight
            
            scores.append(MatrixScore(
                criterion=c_name,
                option=opt,
                evidence_snippet=a.get("evidence_snippet", ""),
                source_id=str(a.get("source_id", "")),
                categorical_assessment=assess,
                numeric_score=n_score,
                weight=weight,
                weighted_score=weighted_score
            ))
            
            if opt not in total_scores:
                total_scores[opt] = 0.0
            total_scores[opt] += weighted_score
            
        return valid_criteria, scores, total_scores

analyzers = Analyzers()
