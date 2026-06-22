# Follow the idea — Turn 1: how the critic's correction reached the writer

Topic: *the core math and ML foundations a beginner should learn first*

This exhibit traces seven ML concepts that are **absent** from the researcher's
finding, **introduced** by the critic, and then **adopted** by the writer. The
writer never spoke to the critic — the only channel between them is coilmem's
`shared` scope. So any critic-originated term in the writer's output arrived via
shared memory.

## 1. The term ledger (computed from the raw text)

| ML concept | researcher (#1) | critic (#3) | writer (#5) |
|---|:---:|:---:|:---:|
| supervised | ✗ | ✓ | ✓ |
| unsupervised | ✗ | ✓ | ✓ |
| overfitting | ✗ | ✓ | ✓ |
| bias-variance | ✗ | ✓ | ✓ |
| cross-validation | ✗ | ✓ | ✓ |
| precision | ✗ | ✓ | ✓ |
| recall | ✗ | ✓ | ✓ |

**7/7 terms are absent from the researcher.** **7/7** of those appear in BOTH the critic and the writer —
i.e. the writer's only possible source for them is the critic's shared memory.

## 2. What fed the writer before it wrote (from recall_log.json)

```
[researcher/CROSS-SHARED score=0.7677] To effectively embark on a journey in machine learning (ML), beginners should focus on a s...
[critic/CROSS-SHARED score=0.6477] # Critique of Core Math and ML Foundations Findings

## Strengths
- **Well-organized struc...
```
The writer retrieved the critic's critique (`critic/CROSS-SHARED`). That is the
pipe the terms travelled through.

## 3. The three texts, in order

### A. researcher/shared (#1) — math only, no ML concepts
> To effectively embark on a journey in machine learning (ML), beginners should focus on a solid foundation in both mathematics and the fundamental concepts of ML. Here are 2-3 important findings on the core math and ML foundations that beginners should consider:
> 
> 1. **Linear Algebra**: Understanding concepts in linear algebra is crucial for grasping ML algorithms. Key areas include:
>    - Vectors and matrices: These are foundational structures in ML that represent datasets and features. Operations such as matrix multiplication are essential for understanding how algorithms process and transform data.
>    - Eigenvalues and eigenvectors: These con …

### B. critic/shared (#3) — names the missing ML concepts
> ML practice
> 
> ## Critical Gaps
> 
> ### 1. **Missing Practical ML Foundations**
> - The findings focus *only* on math, not on "core ML foundations" as stated in the topic
> - **Gap**: No mention of fundamental ML concepts like:
>   - Supervised vs. unsupervised learning
>   - Overfitting/underfitting and bias-variance tradeoff
>   - Training/validation/test splits
>   - Cross-validation
>   - Key metrics (precision, recall, AUC, etc.)
> - These are often more immediately useful than calculus for beginners
> 
> ### 2. **Missing Sequencing and Depth Guidance**
> - No indication of *which math to learn first* or in what order
> - **Risk**: A beginner might spend 6 …

### C. writer/shared (#5) — adopts exactly those concepts
> However, to truly support beginners, it is essential to broaden this focus to include core ML concepts. Understanding supervised vs. unsupervised learning, overfitting and underfitting, the bias-variance tradeoff, and model validation and evaluation techniques like cross-validation and performance metrics (e.g., precision, recall) are crucial. This broader perspective will enable beginners to apply mathematical foundations effectively in practice.
> 
> In addition, guiding beginners on the sequence and depth of topics …

## 4. Reading
- The bolded ML terms in **C** (supervised/unsupervised, overfitting,
  bias-variance, cross-validation, precision/recall) do not occur anywhere in **A**.
- They occur in **B**, the critic's critique of **A**.
- The recall log (section 2) proves **B** was in the writer's context when it wrote **C**.
- Therefore the writer's completeness gain is causally attributable to shared memory,
  not to the writer's own reasoning or to the researcher's finding.