# Core Identity & Project Context

## Metadata
- **Project**: NaviAble (Community-driven accessibility enhancement platform)
- **Institution**: Indian Institute of Information Technology (IIIT), Trichy (4th-Year CSE Final Year Project).
- **Team**: Priyanshu Makwana (Lead Developer) & Team 7.
- **Hardware Profile Target**: Windows OS, NVIDIA GTX 1650 Ti GPU, VS Code, PowerShell virtual environments.

## The Problem ("Accessibility Washing")
Locations often claim to be "accessible" to gain favorable reviews, but lack genuine physical infrastructure (ramps, wide doors, grab bars). Generic text reviews ("The food is great and it's accessible") mislead physically and visually impaired users.

## The Solution (Your Mission)
You are building the **Dual-AI Verification Architecture**.
1. **Vision Module**: YOLOv11 analyzes user-uploaded images to detect actual physical infrastructure.
2. **NLP Integrity Engine**: A distilled RoBERTa model analyzes text to filter out generic praise and flag genuine spatial/architectural descriptions.

Your job is to build the full-stack infrastructure (FastAPI + Flutter + PostgreSQL) to serve these pre-trained models, creating a seamless 0-to-100 production platform.