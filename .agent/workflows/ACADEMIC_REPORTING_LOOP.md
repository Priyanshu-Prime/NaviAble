# Workflow: Academic Reporting & Presentation Generation

Execute this loop when the user requests data for project reviews, panel defenses, or LaTeX documentation.

1. **Context Loading**: Read `.agent/system/ACADEMIC_AND_PRESENTATION.md`.
2. **Data Extraction**: If requested, write a Python script using `pandas` and `sklearn.metrics` to process CSV validation data and generate exact numbers.
3. **Visual Generation**: Use `matplotlib` and `seaborn` to generate high-DPI (300dpi) PNGs for Confusion Matrices, Precision-Recall curves, or Loss comparisons. Save to `reports/figures/`.
4. **Narrative Construction**: 
   - Defend Phase A vs Phase B (Ablation study).
   - Defend the YOLO mAP scores realistically.
5. **Formatting**: Provide the final output as strictly formatted LaTeX blocks or sharp, 5-bullet-point presentation scripts. Do not write fluffy, generic text.