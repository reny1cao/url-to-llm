# Premium Content Extraction Plan

## Overview
Design a tiered extraction system where premium users get LLM-enhanced content extraction for better formatting quality, while maintaining the existing free tier with regex-based fixes.

## Goals
1. **Maintain backward compatibility** - Don't break existing functionality
2. **Cost-efficient** - Only use LLM when necessary
3. **Scalable** - Handle both free and premium users efficiently
4. **Quality improvement** - Significant quality boost for premium users
5. **Transparent pricing** - Users understand what they're paying for

## Proposed Tier Structure

### 1. Free Tier
- **Method**: Trafilatura + Regex fixes (current implementation)
- **Quality**: Good (80-90% accuracy)
- **Cost**: $0
- **Limits**: 
  - 1,000 pages/month
  - 10 sites/month
  - 50 pages per crawl

### 2. Premium Tier ($49/month)
- **Method**: Trafilatura + Regex + Selective LLM enhancement
- **Quality**: Excellent (95%+ accuracy)
- **LLM Usage**: Only for pages with quality score < 0.8
- **Cost to us**: ~$0.0004 per page (only 10-20% need LLM)
- **Limits**:
  - 50,000 pages/month
  - 500 sites/month
  - 500 pages per crawl

### 3. Enterprise Tier ($499/month)
- **Method**: Trafilatura + Always LLM enhancement
- **Quality**: Perfect (99%+ accuracy)
- **LLM Usage**: All pages get LLM polish
- **Cost to us**: ~$0.0004 per page
- **Limits**:
  - 1,000,000 pages/month
  - 10,000 sites/month
  - Custom needs

## Technical Architecture

### 1. Extraction Pipeline
```
HTML → Trafilatura → Quality Check → Enhancement Decision → Output
                                    ↓
                            Free: Regex Fixes
                            Premium: Regex + Selective LLM
                            Enterprise: Always LLM
```

### 2. Quality Scoring System
Detect issues to determine if LLM is needed:
- Broken punctuation after code
- Split sentences
- Malformed code blocks
- Broken lists
- Orphaned punctuation
- Overall structure coherence

### 3. LLM Integration Strategy

#### Provider Selection
- **Primary**: Gemini 2.0 Flash ($0.075/M input, $0.30/M output)
- **Fallback**: GPT-4o-mini (if Gemini fails)
- **Free tier option**: Gemini Flash Lite (with rate limits)

#### Cost Optimization
1. **Caching**: Cache LLM-cleaned content by content hash
2. **Batching**: Process multiple pages in single LLM calls
3. **Smart prompts**: Minimal, focused prompts to reduce tokens
4. **Quality threshold**: Only use LLM when really needed

### 4. Implementation Phases

#### Phase 1: Infrastructure (Week 1)
- [ ] Create user tier database schema
- [ ] Add subscription management
- [ ] Set up billing integration
- [ ] Create usage tracking system

#### Phase 2: Extraction Enhancement (Week 2)
- [ ] Build quality scoring system
- [ ] Create LLM integration layer
- [ ] Implement caching system
- [ ] Add fallback mechanisms

#### Phase 3: API Changes (Week 3)
- [ ] Add tier parameter to crawl endpoints
- [ ] Create usage limit enforcement
- [ ] Add quality metrics to responses
- [ ] Build admin dashboard

#### Phase 4: Testing & Optimization (Week 4)
- [ ] A/B test quality improvements
- [ ] Optimize LLM prompts
- [ ] Fine-tune quality thresholds
- [ ] Load testing

## Database Schema Changes

```sql
-- User tiers
CREATE TABLE user_subscriptions (
    user_id UUID PRIMARY KEY,
    tier VARCHAR(20) NOT NULL DEFAULT 'free',
    started_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP,
    stripe_subscription_id VARCHAR(255)
);

-- Usage tracking
CREATE TABLE extraction_usage (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    crawl_id UUID NOT NULL,
    pages_extracted INT NOT NULL,
    llm_enhanced_pages INT DEFAULT 0,
    llm_tokens_used INT DEFAULT 0,
    extraction_cost DECIMAL(10,6),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Quality metrics
CREATE TABLE extraction_quality (
    page_id UUID PRIMARY KEY,
    quality_score DECIMAL(3,2),
    issues_detected JSONB,
    llm_used BOOLEAN DEFAULT FALSE,
    extraction_method VARCHAR(50)
);
```

## API Changes

### Crawl Endpoint Enhancement
```python
POST /api/crawl
{
    "url": "https://example.com",
    "max_pages": 50,
    "extraction_tier": "premium"  # optional, defaults to user's tier
}

Response:
{
    "crawl_id": "...",
    "pages": [...],
    "extraction_quality": {
        "average_score": 0.95,
        "llm_enhanced_count": 5,
        "method": "trafilatura_regex_selective_llm"
    },
    "usage": {
        "pages_used": 50,
        "monthly_remaining": 49950
    }
}
```

## Cost Analysis

### Premium Tier Economics
- **Revenue**: $49/month
- **Costs**:
  - LLM (20% of 50k pages): ~$3.75
  - Infrastructure: ~$5
  - **Profit margin**: ~82%

### Enterprise Tier Economics
- **Revenue**: $499/month
- **Costs**:
  - LLM (100% of 100k pages): ~$37.50
  - Infrastructure: ~$50
  - Dedicated support: ~$100
  - **Profit margin**: ~62%

## Risk Mitigation

1. **LLM Provider Outages**
   - Fallback to regex-only mode
   - Multiple provider support
   - Graceful degradation

2. **Cost Overruns**
   - Hard limits on LLM usage
   - Real-time cost monitoring
   - Automatic cutoffs

3. **Quality Issues**
   - A/B testing framework
   - User feedback system
   - Quick rollback capability

## Success Metrics

1. **Quality Improvement**
   - Target: 50% reduction in formatting issues for premium
   - Measure: Automated quality scoring + user feedback

2. **Conversion Rate**
   - Target: 5% of free users → premium
   - Premium retention: 90%+ monthly

3. **Cost Efficiency**
   - LLM cost < 10% of revenue
   - Cache hit rate > 30%

## Next Steps

1. **Review and approve plan**
2. **Set up development environment**
3. **Create feature branch**
4. **Begin Phase 1 implementation**

## Questions to Resolve

1. Should we offer a 14-day free trial of premium?
2. How do we handle existing users during migration?
3. Should enterprise tier include API access?
4. Do we need a "pay-as-you-go" option for occasional users?
5. How do we handle rate limiting for LLM calls?