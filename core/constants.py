"""
Versatile-Memory v2 — Sistem Sabitleri

Tüm namespace, relation type, data class ve status değerleri
burada tanımlanır. Tek kaynak (single source of truth).
"""

# ── Namespace'ler ──────────────────────────────────────────────────────────────
# Mimari v2: code | user | project | runtime | incident | reasoning
VALID_NAMESPACES = frozenset({
    "code",       # Codebase index (fonksiyonlar, servisler, config)
    "user",       # Kullanıcı davranışları ve tercihleri (proje-scoped)
    "project",    # Mimari kararlar, sistem tasarımları
    "runtime",    # Geçici context (aktif task sırasında)
    "incident",   # Hata geçmişleri, postmortem
    "reasoning",  # Agent Düşünce zincirleri, hypothesis, decision trace
})

# ── Node Status ────────────────────────────────────────────────────────────────
STATUS_ACTIVE = "active"
STATUS_DEPRECATED = "deprecated"
VALID_STATUSES = frozenset({STATUS_ACTIVE, STATUS_DEPRECATED})

# ── Data Classification ───────────────────────────────────────────────────────
# Memory Layer
DATA_CLASS_GROUND_TRUTH = "ground_truth"
DATA_CLASS_VERIFIED = "verified"
DATA_CLASS_DISTILLED = "distilled"  # Reasoning → Memory terfi

# Reasoning Layer
DATA_CLASS_INFERENCE = "inference"
DATA_CLASS_DECISION = "decision"
DATA_CLASS_HYPOTHESIS = "hypothesis"
DATA_CLASS_SPECULATION = "speculation"

MEMORY_DATA_CLASSES = frozenset({
    DATA_CLASS_GROUND_TRUTH,
    DATA_CLASS_VERIFIED,
    DATA_CLASS_DISTILLED,
})

REASONING_DATA_CLASSES = frozenset({
    DATA_CLASS_INFERENCE,
    DATA_CLASS_DECISION,
    DATA_CLASS_HYPOTHESIS,
    DATA_CLASS_SPECULATION,
})

ALL_DATA_CLASSES = MEMORY_DATA_CLASSES | REASONING_DATA_CLASSES

# ── Relation Types (Edge) ─────────────────────────────────────────────────────
RELATION_DEPENDS_ON = "depends_on"
RELATION_CALLS = "calls"
RELATION_OWNS = "owns"
RELATION_DERIVES_FROM = "derives_from"
RELATION_RELATED_TO = "related_to"
RELATION_IMPORTS = "imports"
RELATION_IMPLEMENTS = "implements"
RELATION_SUPERSEDES = "supersedes"

VALID_RELATION_TYPES = frozenset({
    RELATION_DEPENDS_ON,
    RELATION_CALLS,
    RELATION_OWNS,
    RELATION_DERIVES_FROM,
    RELATION_RELATED_TO,
    RELATION_IMPORTS,
    RELATION_IMPLEMENTS,
    RELATION_SUPERSEDES,
})

# ── Reasoning Session Status ──────────────────────────────────────────────────
SESSION_ACTIVE = "active"
SESSION_COMPLETED = "completed"
SESSION_ABANDONED = "abandoned"
VALID_SESSION_STATUSES = frozenset({SESSION_ACTIVE, SESSION_COMPLETED, SESSION_ABANDONED})

# ── ChromaDB ───────────────────────────────────────────────────────────────────
CHROMA_COLLECTION_NAME = "memory_vectors"

# Source type markers in ChromaDB metadata
SOURCE_TYPE_MEMORY = "memory"
SOURCE_TYPE_REASONING = "reasoning"

# ── Sistem Kuralları ───────────────────────────────────────────────────────────
# Memory asla silinmez. Bu sabittir.
ALLOW_HARD_DELETE = False
