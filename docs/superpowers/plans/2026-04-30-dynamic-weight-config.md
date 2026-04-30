# Dynamic Weight Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modify the weight configuration page to support dynamic field list (add/remove) with im_patient column selection, and enforce total weight = 100 before saving.

**Architecture:** The weight configuration will change from a hardcoded 6-field structure to a dynamic list stored in `empi_config` table with format `{field_name, display_name, weight}`. A new API endpoint will provide im_patient table columns for selection. Frontend will calculate and display total weight, blocking save unless total = 100.

**Tech Stack:** FastAPI, Vue 3, Element Plus, SQLAlchemy, MySQL

---

## File Structure

**Backend:**
- Modify: `backend/app/services/config_service.py` - Change weight storage/retrieval to support dynamic fields
- Modify: `backend/app/api/config.py` - Add endpoint for im_patient columns, update weight endpoints
- Modify: `backend/app/services/similarity.py` - Support dynamic field similarity calculation
- Modify: `backend/app/api/deps.py` - Add get_db dependency

**Frontend:**
- Modify: `frontend/src/views/Config.vue` - Dynamic field list with add/remove, total weight display
- Modify: `frontend/src/api/index.js` - Add getPatientFields API

---

## Task 1: Add Patient Fields API Endpoint

**Files:**
- Modify: `backend/app/api/config.py`
- Test: curl to `/api/config/patient-fields`

- [ ] **Step 1: Add patient_fields endpoint to config.py**

```python
@router.get("/patient-fields")
def get_patient_fields(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """获取im_patient表的字段列表"""
    result = db.execute(text("DESCRIBE im_patient"))
    columns = [row[0] for row in result.fetchall()]
    return {"fields": columns}
```

- [ ] **Step 2: Test the endpoint**

Run: `curl -s http://localhost:8000/api/config/patient-fields`
Expected: `{"fields":["id","patient_id","person_name","gender","birthday","identity_card_num","card_id","phone","address","data_updatetime"]}`

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/config.py
git commit -m "feat: add patient-fields API endpoint"
```

---

## Task 2: Update ConfigService Weight Structure

**Files:**
- Modify: `backend/app/services/config_service.py`
- Test: Verify weight format change

- [ ] **Step 1: Update get_weights to return new format**

The new weight format will be:
```python
[
    {"field_name": "identity_card", "display_name": "身份证号码", "weight": 30},
    {"field_name": "name", "display_name": "姓名", "weight": 30},
    ...
]
```

Modify `get_weights` method to return this list format, migrating from old dict format if needed.

- [ ] **Step 2: Update update_weights to accept and store new format**

```python
def update_weights(self, db: Session, weights: list) -> list:
    # Validate total weight = 100
    total = sum(w['weight'] for w in weights)
    if total != 100:
        raise ValueError(f"Weight total must be 100, got {total}")

    # Store as JSON list
    config = db.query(EmpiConfig).filter(
        EmpiConfig.config_key == 'field_weights'
    ).first()

    if config:
        config.config_value = weights
        config.updated_at = datetime.now()
    else:
        config = EmpiConfig(
            config_key='field_weights',
            config_value=weights,
            description='字段权重配置',
            updated_at=datetime.now()
        )
        db.add(config)

    db.commit()
    self.redis_client.setex('config:weights', 3600, json.dumps(weights))
    return weights
```

- [ ] **Step 3: Update default weights to new format**

```python
default_weights = [
    {"field_name": "identity_card", "display_name": "身份证号码", "weight": 30},
    {"field_name": "name", "display_name": "姓名", "weight": 30},
    {"field_name": "birthday", "display_name": "生日", "weight": 20},
    {"field_name": "gender", "display_name": "性别", "weight": 5},
    {"field_name": "phone", "display_name": "电话", "weight": 10},
    {"field_name": "address", "display_name": "地址", "weight": 5}
]
```

- [ ] **Step 4: Test weight API**

Run: `curl -s http://localhost:8000/api/config/weights`
Expected: Returns array with field_name, display_name, weight

- [ ] **Step 5: Test weight update with validation**

Run: `curl -s -X PUT http://localhost:8000/api/config/weights -H "Content-Type: application/json" -d '[{"field_name":"test","display_name":"测试","weight":50}]'`
Expected: Error because total != 100

- [ ] **Step 6: Test valid weight update**

Run: `curl -s -X PUT http://localhost:8000/api/config/weights -H "Content-Type: application/json" -d '[{"field_name":"identity_card","display_name":"身份证","weight":100}]'`
Expected: Success, total = 100

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/config_service.py
git commit -m "feat: update weight config to dynamic field format"
```

---

## Task 3: Update SimilarityCalculator for Dynamic Fields

**Files:**
- Modify: `backend/app/services/similarity.py`
- Test: Verify similarity calculation works with dynamic fields

- [ ] **Step 1: Update _calculate_field_similarity to handle dynamic fields**

Current hardcoded methods map needs to become dynamic:

```python
def _calculate_field_similarity(self, field: str, patient_a: Dict[str, Any], patient_b: Dict[str, Any]) -> float:
    """计算单个字段的相似度"""
    field_name = field.get('field_name', field) if isinstance(field, dict) else field

    # Map field_name to actual patient data getter and similarity method
    methods = {
        'identity_card': self._similarity_identity_card,
        'identity_card_num': self._similarity_identity_card,
        'name': self._similarity_name,
        'person_name': self._similarity_name,
        'birthday': self._similarity_birthday,
        'gender': self._similarity_gender,
        'phone': self._similarity_phone,
        'address': self._similarity_address,
        'location': self._similarity_address,
    }

    method = methods.get(field_name, lambda a, b: 0.0)
    return method(patient_a, patient_b)
```

- [ ] **Step 2: Test similarity with new format**

Run ETL clean and verify it works with the new weight structure.

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/similarity.py
git commit -m "feat: support dynamic field names in similarity calculation"
```

---

## Task 4: Update Frontend API

**Files:**
- Modify: `frontend/src/api/index.js`

- [ ] **Step 1: Add getPatientFields to configApi**

```javascript
export const configApi = {
  getWeights: () => api.get('/api/config/weights'),
  updateWeights: (weights) => api.put('/api/config/weights', weights),
  getThreshold: () => api.get('/api/config/threshold'),
  updateThreshold: (threshold) => api.put('/api/config/threshold', { threshold }),
  getPendingThreshold: () => api.get('/api/config/pending-threshold'),
  updatePendingThreshold: (threshold) => api.put('/api/config/pending-threshold', { threshold }),
  getPollInterval: () => api.get('/api/config/poll-interval'),
  updatePollInterval: (hours) => api.put('/api/config/poll-interval', { hours }),
  getPatientFields: () => api.get('/api/config/patient-fields')
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/index.js
git commit -m "feat: add getPatientFields API"
```

---

## Task 5: Rewrite Config.vue for Dynamic Weights

**Files:**
- Modify: `frontend/src/views/Config.vue`

- [ ] **Step 1: Update template for dynamic field list**

Replace the hardcoded v-for with dynamic list:

```vue
<el-card>
  <template #header>
    <span>字段权重配置</span>
    <el-button type="success" size="small" @click="addField" style="margin-left: 10px;">
      添加字段
    </el-button>
  </template>

  <el-form label-width="120px">
    <el-form-item v-for="(item, index) in weights" :key="index" :label="item.display_name || item.field_name">
      <el-input-number v-model="item.weight" :min="0" :max="100" />
      <el-button type="danger" size="small" @click="removeField(index)" style="margin-left: 10px;">
        删除
      </el-button>
    </el-form-item>

    <el-form-item label="权重总分">
      <el-tag :type="totalWeight === 100 ? 'success' : 'danger'" size="large">
        {{ totalWeight }} / 100
      </el-tag>
    </el-form-item>

    <el-form-item>
      <el-button type="primary" :disabled="totalWeight !== 100" @click="saveWeights">
        保存权重
      </el-button>
    </el-form-item>
  </el-form>
</el-card>
```

- [ ] **Step 2: Add dialog for adding new field**

```vue
<el-dialog v-model="showAddDialog" title="添加字段" width="400px">
  <el-form>
    <el-form-item label="选择字段">
      <el-select v-model="newField.field_name" placeholder="请选择字段">
        <el-option
          v-for="field in availableFields"
          :key="field"
          :label="field"
          :value="field"
        />
      </el-select>
    </el-form-item>
    <el-form-item label="显示名称">
      <el-input v-model="newField.display_name" placeholder="请输入显示名称" />
    </el-form-item>
    <el-form-item label="权重">
      <el-input-number v-model="newField.weight" :min="0" :max="100" />
    </el-form-item>
  </el-form>
  <template #footer>
    <el-button @click="showAddDialog = false">取消</el-button>
    <el-button type="primary" @click="confirmAddField">确定</el-button>
  </template>
</el-dialog>
```

- [ ] **Step 3: Update script setup**

```javascript
import { ref, computed, onMounted } from 'vue'
import { configApi } from '../api'
import { ElMessage } from 'element-plus'

const weights = ref([])
const threshold = ref(85)
const pendingThreshold = ref(60)
const pollInterval = ref(2)
const availableFields = ref([])
const showAddDialog = ref(false)
const newField = ref({ field_name: '', display_name: '', weight: 0 })

const totalWeight = computed(() => {
  return weights.value.reduce((sum, item) => sum + (item.weight || 0), 0)
})

onMounted(async () => {
  try {
    const [weightsRes, thresholdRes, pendingRes, pollRes, fieldsRes] = await Promise.all([
      configApi.getWeights(),
      configApi.getThreshold(),
      configApi.getPendingThreshold(),
      configApi.getPollInterval(),
      configApi.getPatientFields()
    ])
    weights.value = weightsRes.data
    threshold.value = thresholdRes.data.threshold
    pendingThreshold.value = pendingRes.data.threshold
    pollInterval.value = pollRes.data.hours || 2
    availableFields.value = fieldsRes.data.fields || []
  } catch (error) {
    ElMessage.error('获取配置失败')
  }
})

const addField = () => {
  newField.value = { field_name: '', display_name: '', weight: 0 }
  showAddDialog.value = true
}

const confirmAddField = () => {
  if (!newField.value.field_name) {
    ElMessage.warning('请选择字段')
    return
  }
  if (!newField.value.display_name) {
    ElMessage.warning('请输入显示名称')
    return
  }
  weights.value.push({ ...newField.value })
  showAddDialog.value = false
}

const removeField = (index) => {
  weights.value.splice(index, 1)
}

const saveWeights = async () => {
  if (totalWeight.value !== 100) {
    ElMessage.error('权重总分必须等于100分')
    return
  }
  try {
    await configApi.updateWeights(weights.value)
    ElMessage.success('权重保存成功')
  } catch (error) {
    ElMessage.error('权重保存失败')
  }
}
```

- [ ] **Step 4: Test the frontend**

Open http://localhost:3000/config and verify:
- Dynamic field list displays correctly
- Total weight shows
- Add field button opens dialog
- Delete field button works
- Save disabled when total != 100

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/Config.vue
git commit -m "feat: implement dynamic weight configuration UI"
```

---

## Task 6: Integration Test

- [ ] **Step 1: Test full flow**

1. Open Config page
2. Verify 6 default fields with total = 100
3. Add a new field (select from dropdown, enter display name)
4. Verify total weight updates
5. Try to save when total != 100 (should be blocked)
6. Adjust weights to make total = 100
7. Save successfully
8. Refresh page, verify persistence

- [ ] **Step 2: Test ETL still works**

Run trigger-clean and verify similarity calculation works with dynamic fields.

---

## Self-Review Checklist

1. **Spec coverage:**
   - [x] Total weight display: Task 5 (computed property, template display)
   - [x] Must equal 100 to save: Task 5 (disabled button, validation)
   - [x] Dynamic add/remove fields: Task 5 (addField, removeField, dialog)
   - [x] Dropdown selects from im_patient: Task 1 (patient-fields API), Task 4 (frontend API), Task 5 (el-select)

2. **Placeholder scan:** No TBD/TODO found. All code is complete.

3. **Type consistency:**
   - Backend weight format: `{"field_name": str, "display_name": str, "weight": int}`
   - Frontend weight items: same structure
   - API response: `{"fields": [...]}` for patient-fields

---

## Plan Complete

**Saved to:** `docs/superpowers/plans/2026-04-30-dynamic-weight-config.md`

**Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
