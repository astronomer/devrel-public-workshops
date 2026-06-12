"""Shared Asset definitions wiring the AIMLOps workshop DAGs together.

Centralised so the cross-DAG Asset names never drift across the DAGs
(see the design spec section 4 for the architecture diagram). Each DAG imports
the Assets it produces (outlets) or consumes (schedule) from here.
"""

from airflow.sdk import Asset

# The prospect email loop.
INBOUND_PROSPECT_EMAIL = Asset("aimlops/inbound_prospect_email")
MESSAGE_SENT = Asset("aimlops/message_sent")

# The context store.
CONTEXT_UNITS_UPDATED = Asset("aimlops/context_units_updated")
RAG_INDEX_UPDATED = Asset("aimlops/rag_index_updated")

# Features and model registry.
DETERMINISTIC_FEATURES_READY = Asset("aimlops/deterministic_features_ready")
AI_FEATURES_READY = Asset("aimlops/ai_features_ready")
MODEL_REGISTERED = Asset("aimlops/model_registered")

# The self-improving loop.
INTERACTION_COMPLETE = Asset("aimlops/interaction_complete")
TRACE_CREATED = Asset("aimlops/trace_created")
OUTCOME_RECORDED = Asset("aimlops/outcome_recorded")
CONTEXT_GRAPH_UPDATED = Asset("aimlops/context_graph_updated")

# Existing MLOps plugin sync channel (produced by dags/plugin_sync.py).
PLUGIN_SYNC = Asset("plugin_sync")
