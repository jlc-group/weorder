---
description: Skills ที่ต้องใช้ในการทำงาน - Verification, Debugging, Session Handoff
---

# Agent Skills

> Skills จาก skills.sh ที่ต้องปฏิบัติตาม

---

## 🔴 1. Verification Before Completion (บังคับ!)

### กฎเหล็ก
```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

### The Gate Function
**ก่อน claim ว่า "เสร็จ" ต้องทำ:**

1. **IDENTIFY** - คำสั่งอะไรที่พิสูจน์ claim นี้?
2. **RUN** - รันคำสั่งนั้น (fresh, complete)
3. **READ** - อ่าน output ทั้งหมด, เช็ค exit code
4. **VERIFY** - output ยืนยัน claim หรือไม่?
5. **ONLY THEN** - ถึงจะบอกว่าเสร็จได้

### ห้ามทำ
- ❌ ใช้คำ "should", "probably", "seems to", "น่าจะ"
- ❌ พูดว่า "Great!", "Perfect!", "Done!" ก่อน verify
- ❌ บอกว่า "แก้แล้ว" โดยไม่ทดสอบ
- ❌ Trust agent success reports โดยไม่ตรวจสอบ

### ต้องทำ
- ✅ รัน test/build/check ก่อนบอกว่าเสร็จ
- ✅ ดู browser/console จริงก่อนบอกว่าใช้งานได้
- ✅ แสดง evidence พร้อมกับ claim ทุกครั้ง

---

## 🟠 2. Systematic Debugging (4 Phases)

### กฎเหล็ก
```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

### The Four Phases

#### Phase 1: Root Cause Investigation
1. อ่าน error messages ละเอียด (อย่าข้าม!)
2. Reproduce consistently - ทำซ้ำได้ไหม?
3. Check recent changes - git diff, recent commits
4. Gather evidence ที่ทุก component boundary

#### Phase 2: Pattern Analysis
- หา patterns ใน failures
- ปัญหาเกิดที่ไหนบ่อย?

#### Phase 3: Hypothesis and Testing
- สร้าง hypothesis
- Test แต่ละ hypothesis

#### Phase 4: Implementation
- แก้ไขหลังจากรู้ root cause เท่านั้น!

### ห้ามทำ
- ❌ แก้แบบเดา (random fixes)
- ❌ Quick patches โดยไม่รู้สาเหตุ
- ❌ แก้ทีละจุดโดยไม่หาปัญหาทั้งหมดก่อน

---

## 🟡 3. Session Handoff

### เมื่อไหร่ต้องสร้าง Handoff
- ทำงานหลายไฟล์ (5+ files)
- Debug ซับซ้อน
- ตัดสินใจสำคัญ
- Context กำลังจะเต็ม

### Handoff Document ต้องมี
1. **Current State** - สถานะปัจจุบัน
2. **Important Context** - ข้อมูลที่ต้องรู้
3. **Next Steps** - ขั้นตอนถัดไป (ชัดเจน!)
4. **Decisions Made** - การตัดสินใจ + เหตุผล

### วิธีใช้
```bash
# สร้าง handoff
# เขียนลง: .agent/handoffs/YYYY-MM-DD-task-slug.md

# Resume จาก handoff
# อ่าน handoff ก่อนเริ่มงาน
```

---

## 📋 Checklist ก่อนบอกว่า "เสร็จ"

```markdown
## Pre-Completion Checklist
- [ ] รัน test/build แล้ว pass
- [ ] ดู browser จริงแล้ว ไม่มี error
- [ ] ทดสอบ feature ที่แก้ไขแล้ว
- [ ] ไม่มี console errors
- [ ] Evidence พร้อมแสดง
```

---

## 🔗 Sources

- [verification-before-completion](https://github.com/obra/superpowers)
- [systematic-debugging](https://github.com/softaworks/agent-toolkit)
- [session-handoff](https://github.com/softaworks/agent-toolkit)
