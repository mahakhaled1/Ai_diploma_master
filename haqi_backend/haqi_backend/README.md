# 🇪🇬 Haqi Egypt Service Guide (حقي) — AI Backend, Database & Evaluation

<div align="center">

![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-336791?style=for-the-badge&logo=postgresql&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-10%2F10_Passing-2ea44f?style=for-the-badge)

**«اعرف حقك، افهم الإجراءات، وخد خطوتك الجاية بثقة.»**

</div>

## 👥 فريق المشروع وتكامل الوحدات (Project Team & Module Integration)

| الاسم | الدور | المسؤوليات ونقاط التكامل داخل `haqi_backend` |
| :--- | :--- | :--- |
| **Maha (مها)** | **Backend, Database & Evaluation Lead** | تطوير FastAPI Backend، تصميم قاعدة بيانات PostgreSQL وسجل البيانات الوصفية، إدارة المستخدمين والجلسات، تطوير Evidence Validation & Safe Abstention بالتعاون مع حسن، وإعداد Benchmark Dataset وتقرير التقييم القياسي. |
| **Hassan (حسن)** | **AI Architecture & RAG Lead** | تنسيق خط أنابيب RAG وتوليد الإجابات المهيكلة المسندة بالأدلة (`app/services/rag_service.py` و`app/services/evidence_validator.py`). |
| **Mohamed Hussein (محمد حسين)** | **Data Collection & Knowledge Base** | تغذية قاعدة المعرفة الرسمية وبيانات قطاع الأحوال المدنية والخدمات الحكومية (`app/seed_data.py` و`/api/v1/documents`). |
| **Ahmed Rabie (أحمد ربيع)** | **Arabic NLP & Query Understanding** | تطبيع النص العربي، معالجة العامية المصرية، تصنيف القصد (Intent/NER)، وإعادة صياغة الاستعلام (`app/services/nlp_integration.py`). |
| **Anas (أنس)** | **Retrieval & Search Engineering** | البحث الهجين (Semantic + BM25)، التصفية بالبيانات الوصفية (Metadata Filtering)، وإعادة الترتيب (Cross-Encoder Reranking) (`app/services/retrieval_integration.py`). |
| **Heba (هبة)** | **Frontend & User Experience** | واجهة الويب العربية (RTL Web App)، مستكشف الخدمات والإجراءات، وربط المحادثة التفاعلية عبر REST API (`main.py`). |

## 📂 هيكل المجلد (Directory Structure)

```text
haqi_backend/
├── app/
│   ├── __init__.py
│   ├── config.py                     # إعدادات النظام والاتصال بقاعدة البيانات ومعايير التحقق
│   ├── models.py                     # نماذج SQLAlchemy 2.0 ORM لقاعدة بيانات PostgreSQL
│   ├── database.py                   # مدير قاعدة البيانات (PostgreSQL + SQLite Fallback تلقائي)
│   ├── schemas.py                    # نماذج Pydantic للطلبات والاستجابات المهيكلة
│   ├── seed_data.py                  # قاعدة المعرفة الرسمية الموثقة (قطاع الأحوال المدنية والخدمات)
│   ├── services/
│   │   ├── nlp_integration.py        # وحدة فهم اللغة العربية واللهجة المصرية وتحديد الأسئلة التوضيحية
│   │   ├── retrieval_integration.py  # منظومة البحث الهجين (Semantic + BM25) وإعادة الترتيب
│   │   ├── evidence_validator.py     # آلية ضمان الموثوقية وكشف التعارض والامتناع الآمن (Safe Abstention)
│   │   └── rag_service.py            # منسق رحلة المستخدم (9 خطوات) وتوليد الإجابة المهيكلة بالمصادر
│   └── evaluation/
│       ├── benchmark_dataset.json    # مجموعة بيانات التقييم المرجعية (12 حالة اختبار عربية)
│       └── evaluator.py              # محرك حساب مقاييس الاسترجاع والجودة والأمان والزمن
├── sql/
│   └── schema.sql                    # مخطط جداول PostgreSQL الكامل (Metadata Schema + Sessions + Evaluation)
├── tests/
│   └── test_haqi_backend.py          # اختبارات الوحدات والتكامل الشاملة (10 اختبارات آلية)
├── main.py                           # تطبيق FastAPI ونقاط النهاية (API Endpoints)
├── EVALUATION_REPORT.md              # تقرير التقييم الكمي والنوعي النهائي للنظام
├── Dockerfile                        # ملف بناء حاوية Docker للواجهة الخلفية
├── docker-compose.yml                # تشغيل PostgreSQL 16 + FastAPI Backend معاً
├── requirements.txt                  # الحزم والمكتبات المطلوبة
├── .env.example                      # نموذج متغيرات البيئة (بدون بيانات سرية)
└── .gitignore                        # استبعاد venv وملفات البيئة المؤقتة
```

## 🗄️ تصميم قاعدة البيانات وسجل البيانات الوصفية (PostgreSQL & Metadata Schema)

يطبق النظام الحقول الثمانية لسجل البيانات الوصفية للوثائق الحكومية الرسمية (`official_documents`) بالإضافة إلى جداول المقاطع الإجرائية والجلسات والتقييم:
1. **عنوان الوثيقة (`title`)**
2. **الجهة الحكومية (`authority`)**
3. **الرابط الأصلي (`original_url`)**
4. **تاريخ النشر (`publication_date`)**
5. **تاريخ التحديث (`last_updated`)**
6. **فئة الخدمة (`service_category`)**
7. **تاريخ التحقق (`verification_date`)**
8. **إصدار الوثيقة (`version`)**

> **ملاحظة تشغيلية:** يتصل `app/database.py` تلقائياً بقاعدة بيانات **PostgreSQL** المعرفة في `DATABASE_URL`، وفي حال عدم تشغيل خادم PostgreSQL محلياً أثناء التطوير أو الاختبار السريع، يتحول تلقائياً إلى قاعدة بيانات **SQLite** محلية مع تغذية البيانات الأولية (`seed_data.py`) لضمان عمل المشروع فوراً دون أي أعطال.

## 🌐 نقاط النهاية البرمجية (API Endpoints)

| الطريقة | المسار (Endpoint) | الوظيفة |
| :--- | :--- | :--- |
| `GET` | `/` | فحص حالة الخادم الأساسي (`{"status": "online", "developer": "Maha"}`). |
| `GET` | `/api/v1/health` | تقرير حالة النظام وقاعدة البيانات وعدد الوثائق الرسمية وحالة الوحدات المدمجة. |
| `POST` | `/api/v1/chat` | نقطة المحادثة الرئيسية (تدعم الحوار متعدد الجولات، الأسئلة التوضيحية، الإجابات المهيكلة بالمصادر، والامتناع الآمن). |
| `POST` | `/api/v1/sessions` | إنشاء أو استرجاع جلسة محادثة لمستخدم. |
| `GET` | `/api/v1/sessions/{session_id}` | استرجاع سجل رسائل جلسة محادثة مع المصادر الموثقة. |
| `DELETE` | `/api/v1/sessions/{session_id}` | حذف جلسة المحادثة ورسائلها التزاماً بضوابط الخصوصية وتقليل البيانات (Data Minimization). |
| `GET` | `/api/v1/services` | مستكشف الخدمات الحكومية وتصفية الإجراءات حسب القطاع. |
| `GET` | `/api/v1/services/{service_slug}` | عرض تفاصيل وخطوات ومستندات خدمة محددة (`national-id`, `birth-certificate`, `family-record`, إلخ). |
| `POST` | `/api/v1/services/{service_slug}/check-eligibility` | فاحص الأهلية والمستندات الناقصة التفاعلي وحساب نسبة جاهزية الأوراق. |
| `GET` | `/api/v1/documents` | عرض سجل الوثائق الحكومية الرسمية بالبيانات الوصفية الثمانية. |
| `POST` | `/api/v1/documents` | تسجيل أو تحديث وثيقة رسمية جديدة في قاعدة المعرفة. |
| `POST` | `/api/v1/validate` | نقطة تحقق مستقلة لفحص كفاية الأدلة، موثوقية المصدر، وتأصيل الإجابة. |
| `GET` | `/api/v1/contradictions` | عرض قائمة التعارضات المكتشفة بين المصادر الرسمية والمحالة للمراجعة البشرية. |
| `POST` | `/api/v1/contradictions/{flag_id}/resolve` | حسم التعارض بواسطة المراجع البشري وتحديد الوثيقة المعتمدة. |
| `POST` | `/api/v1/feedback` | تسجيل تقييم المواطن لجودة الإجابة والمصادر. |
| `POST` | `/api/v1/evaluation/run` | تشغيل التقييم القياسي على `benchmark_dataset.json` وحفظ النتائج. |
| `GET` | `/api/v1/evaluation/report` | استرجاع أحدث تقرير تقييم كمي ونوعي للنظام. |

## 🚀 خطوات التشغيل المحلي والاختبار (Local Setup & Testing)

### 1. تثبيت المتطلبات وتشغيل الخادم محلياً
```bash
cd haqi_backend
python -m venv venv
# على Windows:
venv\\Scripts\\activate
# على Linux / macOS:
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --port 8000
```
افتح المتصفح على `http://localhost:8000/docs` لتجربة جميع الـ APIs عبر واجهة Swagger التفاعلية.

### 2. التشغيل عبر Docker & PostgreSQL
```bash
docker compose up --build -d
```

### 3. تشغيل الاختبارات الآلية (Unit & Integration Tests)
```bash
python -m unittest discover -s tests -v
# أو باستخدام pytest:
pytest -v
```
