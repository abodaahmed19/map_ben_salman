# محور طريق محمد بن سلمان — منصة متابعة الجسور والعيوب

منصة لعرض جسور المحور على خريطة قمر صناعي، كل جسر **نقطة بإحداثيات** وله عيوب بصور ووصف وحالة وقياسات.
مبنية بهوية **أمانة العاصمة المقدسة** — إدارة أصول النقل والبنية التحتية.

## التقنيات
- **الخلفية (Backend):** Python · Django 6 · Django REST Framework
- **قاعدة البيانات:** PostgreSQL (عبر DATABASE_URL)
- **الواجهة (Frontend):** Vue 3 (عبر CDN) + Leaflet.js للخرائط
- خرائط القمر الصناعي من Esri والشوارع من CARTO (بدون مفاتيح API).

## التشغيل
```bash
pip install -r requirements.txt
set DATABASE_URL=postgres://USER:PASSWORD@HOST:PORT/DBNAME
python manage.py migrate
python manage.py seed          # بيانات تجريبية + مستخدم admin
python manage.py runserver
```
ثم افتح:
- صفحة العرض: http://localhost:8000/
- لوحة التحكم: http://localhost:8000/panel/
- إدارة Django: http://localhost:8000/admin/  (admin / admin12345)

> على ويندوز إن ظهرت مشكلة ترميز في الطرفية: `set PYTHONUTF8=1` قبل تشغيل الأوامر.

## طريقة الاستخدام (لوحة التحكم)
1. **«إضافة جسر»** → انقر على الخريطة لتحديد موقع الجسر (نقطة).
2. عدّل بيانات الجسر (الاسم، الحالة) — تُحفظ تلقائيًا. ويمكن **«تحريك الموقع»**.
3. **«إضافة عيب»** → اكتب بياناته (الاسم، الحالة، الوصف، الطول، العرض، المساحة، العدد)، احفظ، ثم **ارفع الصور**.
4. كل التعديلات تظهر فورًا في صفحة العرض (نفس قاعدة البيانات).

## البنية
```
config/        إعدادات المشروع (settings, urls, wsgi)
bridges/       تطبيق الجسور: models, serializers, views (DRF), admin, seed
templates/     index.html (العرض) · panel.html (لوحة التحكم)  [Vue داخل {% verbatim %}]
static/        css/styles.css · js/viewer.js · js/panel.js · img/logo.png
media/         صور العيوب المرفوعة
db.sqlite3     قاعدة البيانات
```

## نقاط الـ API
| الطريقة | المسار | الوظيفة |
|--------|--------|---------|
| GET/POST | `/api/bridges/` | عرض/إضافة جسر |
| GET/PUT/PATCH/DELETE | `/api/bridges/{id}/` | تعديل/حذف جسر |
| GET/POST | `/api/defects/` | عرض/إضافة عيب |
| POST | `/api/defects/{id}/upload/` | رفع صور للعيب (multipart) |
| DELETE | `/api/images/{id}/` | حذف صورة |

## ملاحظات الهوية
- الألوان مستخرجة من دليل الهوية: أخضر داكن `#183028` · ذهبي `#b1924a` · أخضر نعناعي `#88c0b0` · أخضر اللوجو `#24423c`.
- خطوط الهوية الرسمية (Lyon Arabic / Ping AR) تجارية؛ استُخدم بديل ويب مجاني قريب: **Tajawal** (مع IBM Plex Sans Arabic احتياطيًا).
- شعار الأمانة في `static/img/logo.png` (النسخة البيضاء على خلفية شفافة).
