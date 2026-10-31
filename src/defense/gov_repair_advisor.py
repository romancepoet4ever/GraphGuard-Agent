from __future__ import annotations


ACTION_LABELS = {
    "block_sensitive_content": "阻断高敏原文输出",
    "isolate_referee_context": "隔离裁判上下文",
    "downgrade_or_label_unverified_claim": "降级并标注未证实陈述",
    "quarantine_poisoned_material": "隔离疑似投毒材料",
    "block_or_sanitize": "阻断或净化越权指令",
    "deny_retrieval_and_log": "拒绝越权检索并审计留痕",
    "mask_personal_information": "个人信息脱敏输出",
    "refuse_and_restore_role": "拒绝角色逃逸并恢复系统角色",
    "allow": "允许执行",
}


class GovRepairAdvisor:
    def label(self, action: str) -> str:
        return ACTION_LABELS.get(action, action)
