# NexForge Architectural Principles

## The 15 Immutable Laws

1. **Invariants are DATA, never executable code.**
2. **AI never writes runtime logic.**
3. **Generated systems are deterministic.**
4. **Safety path is isolated from communication.**
5. **Runtime owns execution, AI owns specification only.**
6. **Every CPS domain compiles into the same execution contract.**
7. **Physics, Safety, Control are orthogonal layers.**
8. **All artifacts are reproducible (content-addressed IR).**
9. **No `eval`/`exec` anywhere.**
10. **Fail-safe > availability.**
11. **Timing is part of the architecture.**
12. **Contracts are assume/guarantee with temporal bounds.**
13. **The architecture itself is an executable contract.**
14. **Hardware capability is a first-class compiler input.**
15. **Deterministic replay is mandatory.**

## Pipeline

