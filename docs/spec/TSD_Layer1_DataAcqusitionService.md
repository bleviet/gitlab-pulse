# **Technical Specification: Layer 1 \- Data Acquisition Service**

**Scope:** Implementation details for the Hybrid Collector (REST \+ GraphQL).

## **1\. System Components**

### **1.1. Ingestion Orchestrator**

The main service loop responsible for:

1. Scanning the environment for PROJECT\_IDS.  
2. Managing the sync\_state.json (tracking last\_updated\_at per project).  
3. Triggering the L0 (Raw) to L1 (Processed) pipeline.

### **1.2. Hybrid API Clients**

* **REST Client:** Wraps python-gitlab. Uses updated\_after filters to perform incremental syncs.  
* **GraphQL Client:** Uses httpx to perform batch queries for "Work Item" widgets (Hierarchy/Parent-Child links) using the project's full\_path.

## **2\. Data Flow & Logic**

### **2.1. The Sync Algorithm**

1. **Check State:** Read data/state/sync\_state.json.  
2. **Fetch REST:** Pull issues updated after the saved timestamp.  
3. **Persist L0:** Save the raw JSON response to data/raw/{project\_id}\_{timestamp}.json for auditing.  
4. **Enrich GQL:** Batch the internal IDs (IIDs) and query GraphQL for hierarchy data.  
5. **Transform:** Use Pydantic to validate and normalize the union of REST \+ GQL data.  
6. **Persist L1:** Upsert into data/processed/issues\_{project\_id}.parquet.

## **3\. Data Model (Pydantic)**

```python
class RawIssue(BaseModel):  
    id: int  
    iid: int  
    project\_id: int  
    title: str  
    description: Optional\[str\] \= None
    state: Literal\['opened', 'closed'\]  
    created\_at: datetime  
    updated\_at: datetime  
    closed\_at: Optional\[datetime\]  
    labels: List\[str\]  
    \# GraphQL Fields  
    work\_item\_type: str \= "ISSUE"  
    parent\_id: Optional\[int\] \= None  
    child\_ids: List\[int\] \= \[\]
```

## **4\. Architecture Decision Records (ADR)**

### **4.1. Why Pydantic instead of Dataclasses?**

* **Coercion:** GitLab API returns ISO strings; Pydantic automatically converts these to Python datetime objects during instantiation.  
* **Deep Validation:** Ensures that nested lists (like labels) are actually lists of strings, preventing downstream "type-errors" in Pandas.

### **4.2. Why Snappy-Compressed Parquet?**

* **Read Speed:** Parquet's columnar format allows L2 to read only the labels and dates columns without loading issue descriptions into memory.  
* **Space:** Snappy provides a balance between compression ratio and CPU speed, ideal for local laboratory servers.
