# DeepSeek-OCR LoRA Fine-Tuning Guide for Bangladeshi Financial Documents

This guide outlines the protocol for parameter-efficient fine-tuning (PEFT / LoRA) of DeepSeek-OCR on challenging real-world Bangladeshi financial documents, specifically targeting low-light mobile photos, skewed angles, and handwritten Bengali cursive in traditional *khata* ledgers.

## 1. Dataset Format & Schema
Fine-tuning data is stored in standard ShareGPT-Vision JSON format with paired document crops:

```json
[
  {
    "id": "bd_doc_001",
    "image": "images/desco_mobile_001.jpg",
    "conversations": [
      {
        "from": "human",
        "value": "<image>\nExtract structured utility bill fields in JSON format."
      },
      {
        "from": "gpt",
        "value": "{\"document_type\": \"utility_bill\", \"provider\": \"DESCO\", \"amount_bdt\": 1450.0, \"due_date\": \"2026-11-25\", \"paid\": true, \"account_or_meter_no\": \"12984012\"}"
      }
    ]
  }
]
```

## 2. Dataset Sizing & Distribution
- **Target Size:** 1,200 to 2,000 paired document images.
- **Stratified Breakdown:**
  - 40% Utility Bills: DESCO, DPDC, Dhaka WASA, Titas Gas, NESCO, BREB (including watermarked and stamped bills).
  - 30% Mobile Financial Services & POS Receipts: bKash agent vouchers, Nagad cash-out slips, Aarong/Shwapno POS receipts.
  - 30% Handwritten Khata Pages: Bengali cursive numbers (০-৯), customer names in Bengali, credit (*baki*) and payment (*joma*) columns.
- **Data Augmentations:** Random perspective skew (±15°), shadow gradient overlays, Gaussian noise, and exposure variation simulating low-cost Android mobile sensors.

## 3. LoRA Configuration & Hyperparameters
- **Base Model:** DeepSeek-VL2 / DeepSeek-OCR vision-language backbone.
- **LoRA Targets:** Vision encoder projection layers (`q_proj`, `v_proj`, `k_proj`, `o_proj`) and language model attention projections.
- **LoRA Rank ($r$):** 32
- **LoRA Alpha ($\alpha$):** 64
- **Dropout:** 0.05
- **Optimizer:** AdamW (`lr=2e-5`, cosine decay with 100 warmup steps).
- **Batch Size:** 16 (per GPU with gradient accumulation steps = 4).
- **Precision:** bfloat16 / 4-bit QLoRA for consumer or single-node 24GB GPUs.

## 4. Execution Command
```bash
# Example fine-tuning launcher using LLaMA-Factory or Deepspeed
deepspeed --num_gpus=4 train_ocr_lora.py \
  --model_name_or_path deepseek-ai/deepseek-vl2 \
  --data_path data/bd_financial_ocr_train.json \
  --output_dir checkpoints/deepseek-ocr-bd-lora \
  --lora_rank 32 \
  --lora_alpha 64 \
  --per_device_train_batch_size 4 \
  --gradient_accumulation_steps 4 \
  --learning_rate 2e-5 \
  --bf16 True \
  --logging_steps 10 \
  --save_strategy "epoch"
```

## 5. Deployment & Runtime Export
Merge the LoRA adapter into the base weights or serve dynamically via vLLM with `--enable-lora`:
```bash
vLLM serve deepseek-ai/deepseek-vl2 --enable-lora --lora-modules ocr-bd=checkpoints/deepseek-ocr-bd-lora
```
Configure `DEEPSEEK_OCR_URL` in `.env` to route through the fine-tuned adapter.
