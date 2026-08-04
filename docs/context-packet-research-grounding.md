# Context Packet Research Grounding

This note maps the context-packet theory used by Reasoning Bridge to current
research, then to concrete recipe/compiler design choices.

It is a design aid, not a literature review. Claims are labeled by strength.

## Operating model

```text
[ Sparse packet ]  → improv / default priors / invented fillers
[ Rich structural ] → activate latent concepts; stabilize generation
[ Over-specified ] → caricature / stereotype amplification
```

Target band for packet recipes:

- high **coverage** of structural variables that would otherwise be improvised
- high **openness** on affect and micro-decisions
- explicit **anti-caricature** guards

These map directly to `ContextPacket.density.coverage`,
`ContextPacket.density.openness`, `locked_variables`, `open_variables`, and
`PacketRecipe.anti_caricature_rules` / `max_stereotype_risk`.

## Claim → evidence → design implication

### 1. Context activates latent structure; it does not teach from scratch

**Strength:** strong

Prompts help a pretrained model locate or select latent concepts already shaped
during training, rather than installing new weights at inference time.

Key references:

- Xie et al., 2021. *An Explanation of In-context Learning as Implicit Bayesian Inference.* ([arXiv:2111.02080](https://arxiv.org/abs/2111.02080))
- Stanford SAIL summary of the same framing: prompts “locate” previously learned concepts. ([blog](https://ai.stanford.edu/blog/understanding-incontext/))
- 2024–2025 ICL analyses continue to emphasize task recognition / hidden-state alignment with latent task structure (e.g. NeurIPS 2024 localization work; later head/task-vector geometry papers).

**Design implication**

- Treat packets as **activation objects**, not knowledge dumps.
- Prefer typed slots that select a neighborhood (`frame`, `identity`,
  `constraints`) over long unstructured transcripts.
- Keep retrieval sources separate from packet compilation: retrieve materials,
  then compile an activation-shaped packet.

### 2. Conditioning narrows the next-token distribution

**Strength:** strong (mechanism wording should stay careful)

Conditioning on role, task, and constraints reduces conditional entropy and
steers generation into a narrower behavioral region. Informal “vector-space
collapse” language is acceptable as metaphor; formal accounts use posterior
sharpening over latent concepts or projection into task subspaces.

**Design implication**

- Compiler should optimize for **distribution shaping**: lock structural vars,
  leave open vars explicit.
- Report density metrics (`coverage`, `openness`, budgets used) so hosts can
  tune recipes toward the rich/optimal band.
- Do not maximize token count. Maximize constrained activation quality.

### 3. Sparse context causes improvisation from priors

**Strength:** strong

When identity or setting is underspecified, models tend to fill gaps with
default personas, corpus averages, or stereotype-linked assumptions rather than
abstaining.

Key references:

- NAACL 2025 work on persona-prompted responses finds a **default persona**
  bias when demographics are omitted
  ([anthology](https://aclanthology.org/2025.naacl-long.50/);
  [arXiv](https://arxiv.org/abs/2503.01532)).
- EMNLP 2025 work on implicit personalization shows models infer demographics
  from stereotypical cues when explicit identity is absent or weak
  ([ACL anthology entry](https://aclanthology.org/2025.emnlp-main.1029/)).

**Design implication**

- Required slots (`frame`, `constraints`, and often `identity` for persona
  agents) exist to prevent improv mode.
- Missing required slots should surface as packet warnings
  (`missing_required_slot:*`), not silent success.
- Prefer explicit `open_vars` when a variable may remain undecided. That is
  better than letting the model invent a filler.

### 4. Rich structural grounding stabilizes behavior

**Strength:** moderate-to-strong, with limits

More specific structural cues generally improve steering and reduce arbitrary
fill-in. Limits matter: post-training assistant priors can be sticky, and
persona adherence is imperfect under conflicting cues.

Related evidence:

- SubPOP (ACL 2025) shows survey-distribution fine-tuning improves opinion
  matching and generalizes to **unseen** demographic subpopulations, supporting
  transferable latent demographic structure
  ([arXiv:2502.16761](https://arxiv.org/abs/2502.16761);
  formerly/often referred to informally as “SUBPO”).
- Persona-collapse / homogenization studies show models can still compress into
  default helpful personas despite role prompts; prompting helps but does not
  guarantee full lock-in.

**Design implication**

- Lock **structural** variables: values, constraints, environment, economic or
  role frame, forbidden moves.
- Do not assume a packet fully overrides the host model’s assistant prior.
- Keep packets inspectable (`provenance`, `warnings`, density) so hosts can
  detect under-constrained compiles.

### 5. Over-specification amplifies caricature and stereotypes

**Strength:** strong

Explicit, heavy-handed persona descriptors—especially essentializing demographic
labels and affect scripts—can increase marked/stereotyped language and reduce
realistic within-group variance.

Key references:

- EMNLP Findings 2025 evaluations of sociodemographic persona prompting
  (“The Prompt Makes the Person(a)”) and related persona/stereotype studies.
- Population-level persona collapse work: models that follow persona prompts
  most strongly can also produce the most demographically caricatured
  populations.

**Design implication**

- `max_stereotype_risk` and `anti_caricature` slots are first-class, not polish.
- Prefer structural claims over “you feel X about every micro-decision.”
- Density profiles (`sparse` / `balanced` / `dense`) and per-slot budgets exist
  to stop “more context is always better.”
- Recipe authors should encode editing/taste/value grammars as constraints and
  examples, not as emotional micromanagement.

### 6. Structural grounding beats affect micromanagement

**Strength:** aligned with best current practice

Interview-style, name-based, or constraint-led priming tends to produce less
marked and more diverse outputs than blunt demographic role assignment.

**Design implication**

Recommended default slot priority for steering recipes:

1. `frame` — world/task neighborhood
2. `constraints` — hard locks / forbidden zones
3. `identity` — role and competence boundary (when needed)
4. `evidence` — grounded retrieved claims
5. `examples` — local style/grammar
6. `open_vars` — explicitly undecided degrees of freedom
7. `anti_caricature` — realism guards

This is exactly the slot vocabulary in `PacketRecipe` / `ContextPacket`.

## SubPOP note

The paper usually cited in this thread is **SubPOP**:

> Suh et al., 2025. *Language Model Fine-Tuning on Scaled Survey Data for
> Predicting Distributions of Public Opinions.* ACL 2025.
> Dataset/code: https://github.com/JosephJeesungSuh/subpop

Useful takeaway for bridge design:

- demographic/subpopulation structure in models can transfer beyond seen groups
- steering prompts matter
- distribution matching is a better target than single stereotyped answers

Caveat:

- SubPOP’s strongest gains come with survey-oriented fine-tuning plus steering.
  It supports the “latent structure exists” claim; it does not prove that
  prompting alone always unlocks high-fidelity personas.

## Recipe authoring checklist

Use this when adding a `PacketRecipe`:

1. What latent neighborhood should this packet activate?
2. Which variables must be locked to prevent improv?
3. Which variables must stay open to avoid caricature?
4. What stereotype risks are plausible for this domain?
5. What budgets keep the packet in the rich/optimal band?
6. Which sources may fill each slot (`SourceBinding`)?
7. How will coverage/openness failures be detected in traces?

## Non-goals

This note does not claim:

- discrete on/off “dormant trait switches” inside the model
- perfect individual-level psychological realism from demographic labels
- that more retrieved tokens automatically improve steering
- that packet compilation replaces model evaluation

## Practical mapping into this repo

| Research need | Bridge primitive |
|---|---|
| Activation object | `ContextPacket` |
| Configurable shape | `PacketRecipe` + `PacketSlotSpec` |
| Multi-source inputs | `FacetMaterial` + `SourceBinding` + facet/context adapters |
| Prevent improv | required slots + `locked_variables` |
| Prevent caricature | `open_variables`, `anti_caricature_rules`, `max_stereotype_risk` |
| Tune density | `density_profile`, budgets, `DensityReport` |
| Inspectability | packet `warnings`, `provenance`, runtime trace events |

When extending the compiler or adding live source adapters (Knowledge Ocean,
LLC containers, chat documents), preserve this mapping: sources emit materials;
recipes define activation geometry; the compiler enforces the sparse/rich/over
continuum.
