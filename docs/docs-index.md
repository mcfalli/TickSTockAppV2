# TickStock Documentation Index

**Purpose**: Central navigation for all TickStock documentation  
**Audience**: Development teams, sprint planning, architecture reference  
**Last Updated**: 2025-08-21  

## 📋 **Quick Reference for Sprint Instructions**

When creating sprint instructions, reference this index to point teams to relevant documentation without embedding full details in sprint documents.

---

## 🗂️ **Documentation Structure**

### 📊 **Core Architecture & System Design**

| Document | Purpose | Use In Sprints |
|----------|---------|---------------|
| `project_overview_detailed.md` | **PRIMARY**: Complete system architecture with visual data pipeline | System understanding, component integration |
| `architecture_overview.md` | High-level system overview | New team member onboarding |
| `technical_overview.md` | Technical implementation details | Development reference |

### 🏗️ **Architecture & Decisions**

| Folder/File | Purpose | Use In Sprints |
|-------------|---------|---------------|
| `architecture/` | Architectural decisions and REST endpoints | Design decisions, API reference |
| `architecture/architectural_decisions.md` | All ADRs (Architectural Decision Records) | Understanding "why" behind architectural choices |
| `design/` | **Multi-Channel Architecture Design** (Sprints 103-108) | Channel implementation, integration patterns |
| `design/multi_channel_architecture.md` | Multi-channel system design specifications | Channel development sprints |
| `design/channel_specifications.md` | Individual channel specifications | Channel-specific development |
| `design/integration_patterns.md` | Integration patterns and guidelines | System integration sprints |

### 📈 **Sprint History & Evolution**

| Folder | Purpose | Use In Sprints |
|--------|---------|---------------|
| `sprints/` | **Complete sprint summaries (105-108)** | Understanding system evolution, architectural context |
| `sprints/sprint-105-completion-summary.md` | Channel Infrastructure implementation | Channel routing development |
| `sprints/sprint-106-completion-summary.md` | Data Type Handlers (Tick, OHLCV, FMV) | Data processing development |
| `sprints/sprint-107-completion-summary.md` | Event Processing Refactor | Event coordination development |
| `sprints/sprint-108-completion-summary.md` | **Integration & Testing** with performance baselines | Performance validation, testing reference |

### 🔧 **Features & Capabilities**

| Folder | Purpose | Use In Sprints |
|--------|---------|---------------|
| `features/` | **Individual feature documentation** | Feature enhancement, debugging |
| `features/event-detection.md` | Event detection systems | Event processing sprints |
| `features/surge-detection.md` | Surge detection algorithms | Algorithm improvement sprints |
| `features/trend-detection.md` | Trend detection systems | Trend analysis enhancement |
| `features/filtering-system.md` | User filtering capabilities | Filtering enhancement sprints |
| `features/memory-first-processing.md` | Memory optimization strategies | Performance optimization sprints |

### 💾 **Data Sources & Configuration**

| Folder | Purpose | Use In Sprints |
|--------|---------|---------------|
| `data_source/` | **Data provider configurations and architectures** | Data integration sprints |
| `data_source/synthetic-data-architecture.md` | Synthetic data system (current) | Testing and development sprints |
| `data_source/settings-configuration.md` | Configuration management | Configuration-related sprints |
| `data_source/single-to-multi-frequency.md` | Data frequency handling | Data processing optimization |

### 🎨 **User Interface & Experience**

| Folder | Purpose | Use In Sprints |
|--------|---------|---------------|
| `UI/` | User interface documentation | Frontend development sprints |
| `UI/grid-stack.md` | Grid layout system | UI enhancement sprints |

### 📋 **Development Instructions & Standards**

| Folder/File | Purpose | Use In Sprints |
|-------------|---------|---------------|
| `instructions/` | **Core development guides and standards** | All development work, code reviews, quality assurance |
| `instructions/unit_testing.md` | **Comprehensive testing guide** - organization, standards, sprint requirements | Testing-focused sprints, quality assurance |
| `instructions/coding-practices.md` | **Complete coding standards** - philosophy, style, error handling, configuration | All development sprints, code reviews |
| `instructions/code-documentation-standards.md` | **Documentation standards** - docstrings, comments, API docs | Documentation sprints, maintenance |
| `instructions/technical-debt-management.md` | **Technical debt process** - identification, prioritization, resolution workflow | Technical debt sprints, maintenance |
| `instructions/architectural-decision-process.md` | **ADR process guide** - decision making, documentation, governance | Architecture sprints, design decisions |
| `instructions/sprint-documentation-tasks.md` | Sprint documentation workflow and requirements | Sprint planning and completion |
| `agents/` | **Configured agent documentation** - Describes active agents, their capabilities and development impact | Understanding available automation tools |

### 🧪 **Testing & Quality (Legacy)**

| Folder | Purpose | Use In Sprints |
|--------|---------|---------------|
| `test/` | Legacy testing documentation (see `instructions/unit_testing.md` for current) | Reference only |

### 🔧 **Maintenance & Operations**

| Folder | Purpose | Use In Sprints |
|--------|---------|---------------|
| `maintenance/` | **Operational procedures and maintenance tasks** | Operations and maintenance sprints |
| `maintenance/maintenance_load_cache_entries.md` | Cache management procedures | Performance maintenance |
| `maintenance/maintenance_load_stocks.md` | Stock data management | Data maintenance sprints |

---

## 🎯 **Sprint Planning Quick Reference**

### **For New Feature Development Sprints**
Point to: `instructions/coding-practices.md`, `instructions/unit_testing.md`, `features/`, `design/integration_patterns.md`, `project_overview_detailed.md`

### **For Architecture/Integration Sprints** 
Point to: `instructions/coding-practices.md`, `design/`, `architecture/`, `sprints/sprint-108-completion-summary.md`

### **For Performance/Optimization Sprints**
Point to: `instructions/coding-practices.md` (performance considerations), `features/memory-first-processing.md`, `sprints/sprint-108-completion-summary.md` (performance baselines)

### **For Data Processing Sprints**
Point to: `instructions/coding-practices.md`, `data_source/`, `features/event-detection.md`, `design/channel_specifications.md`

### **For Frontend/UI Sprints**
Point to: `instructions/coding-practices.md`, `instructions/code-documentation-standards.md`, `UI/`, `architecture/rest-endpoints.md`

### **For Testing/QA Sprints**
Point to: `instructions/unit_testing.md` (**PRIMARY**), `instructions/coding-practices.md`, `sprints/sprint-108-completion-summary.md` (testing framework), `agents/` (automated testing capabilities)

### **For Operations/Maintenance Sprints**
Point to: `instructions/coding-practices.md` (configuration management), `instructions/technical-debt-management.md`, `maintenance/`, `features/`

### **For Code Review & Quality Assurance**
Point to: `instructions/coding-practices.md` (**PRIMARY**), `instructions/code-documentation-standards.md`, `instructions/unit_testing.md`

### **For Architecture & Technical Governance**
Point to: `instructions/architectural-decision-process.md` (**PRIMARY**), `instructions/technical-debt-management.md`, `architecture/architectural_decisions.md`

---

## 📚 **Key Documents by Use Case**

### **System Understanding (New Team Members)**
1. `project_overview_detailed.md` - **START HERE**
2. `sprints/sprint-108-completion-summary.md` - Current system state
3. `instructions/coding-practices.md` - Development standards and practices
4. `instructions/unit_testing.md` - Testing organization and standards
5. `agents/` - Available automation and development tools

### **Multi-Channel Architecture Work**
1. `design/multi_channel_architecture.md` - **Primary reference**
2. `design/channel_specifications.md` - Channel details
3. `sprints/sprint-105-completion-summary.md` through `sprint-108-completion-summary.md` - Evolution
4. `instructions/coding-practices.md` - Implementation best practices

### **Performance & Testing**
1. `instructions/unit_testing.md` - **PRIMARY testing guide**
2. `sprints/sprint-108-completion-summary.md` - Performance baselines and testing framework
3. `features/memory-first-processing.md` - Performance patterns
4. `instructions/coding-practices.md` - Performance considerations

### **Integration & Development**
1. `instructions/coding-practices.md` - **PRIMARY development standards**
2. `instructions/code-documentation-standards.md` - Documentation requirements
3. `design/integration_patterns.md` - Integration guidelines
4. `architecture/architectural_decisions.md` - Decision context

### **Code Quality & Reviews**
1. `instructions/coding-practices.md` - **PRIMARY quality standards**
2. `instructions/code-documentation-standards.md` - Documentation standards
3. `instructions/unit_testing.md` - Testing requirements

---

## 🔄 **Document Maintenance**

### **Living Documents** (Updated Regularly)
- `architecture/architectural_decisions.md` - Add new ADRs each sprint
- `sprints/` - Add new sprint summaries as completed
- `instructions/` - Update development standards as practices evolve
- This `docs-index.md` - Update when structure changes

### **Stable References** (Rarely Changed)
- `project_overview_detailed.md` - Major architecture reference
- `instructions/coding-practices.md` - Core development philosophy and standards
- `instructions/code-documentation-standards.md` - Documentation standards
- `instructions/unit_testing.md` - Testing organization and standards
- `features/` documents - Feature-specific documentation
- `design/` documents - Design specifications

### **Historical References** (Archive Only)
- Sprint summaries become historical once complete
- Superseded design documents moved to archive

---

## 💡 **Usage Guidelines**

### **In Sprint Instructions:**
```markdown
## Development Standards
See: docs/instructions/coding-practices.md (Complete coding standards)
See: docs/instructions/unit_testing.md (Testing requirements)
See: docs/instructions/code-documentation-standards.md (Documentation standards)

## Architecture Reference
See: docs/project_overview_detailed.md (Section: Multi-Channel Processing)
See: docs/sprints/sprint-108-completion-summary.md (Performance Baselines)
See: docs/design/integration_patterns.md (Integration Guidelines)
```

### **For Development Teams:**
- **Always start with** `project_overview_detailed.md` for system understanding
- **Follow** `instructions/coding-practices.md` for all development work
- **Use** `instructions/unit_testing.md` for testing standards and organization
- **Reference** `instructions/code-documentation-standards.md` for documentation requirements
- **Check** `agents/` for available automated development tools and capabilities
- **Reference sprint summaries** for understanding evolution and context
- **Use design documents** for implementation patterns

### **For Sprint Planning:**
- **Always reference** `instructions/` guides for development standards
- **Reference this index** to avoid embedding full documentation in sprint instructions
- **Point to specific sections** rather than entire documents when possible
- **Use sprint summaries** to understand what's already been built
- **Reference performance baselines** from Sprint 108 for performance-related work

### **For Code Reviews:**
- **Primary reference**: `instructions/coding-practices.md` for quality standards
- **Documentation check**: `instructions/code-documentation-standards.md` 
- **Testing validation**: `instructions/unit_testing.md` for test requirements

This index enables lean sprint instructions while ensuring teams have complete access to all necessary architectural and implementation guidance.