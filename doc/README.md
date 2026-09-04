# StratConn - Dependency Graph Documentation

This directory contains comprehensive dependency graphs and analysis of the StratConn codebase.

## Generated Files

### 1. `dependency_graph.md` 📊
A markdown file containing:
- **Visual Mermaid graph** showing all module dependencies and connections
- **Detailed module information** including:
  - List of imports for each module
  - Classes defined in each module
  - Methods/functions defined in each module
  - Method calls made in each module

**Best for:** Reading in GitHub, reviewing text-based documentation

### 2. `dependency_graph.html` 🌐
An interactive D3.js visualization featuring:
- **Draggable force-directed graph** of all modules
- **Color-coded modules** by category:
  - 🔵 Core modules (blue)
  - 🟠 Interface/Gateway modules (orange)
  - 🟢 Strategy/Tracking modules (green)
  - 🔴 Entry point (red)
- **Interactive features:**
  - Click nodes to see module details
  - Search to filter modules
  - Drag nodes to rearrange
  - Hover to see node information
- **Info panels** showing:
  - Classes and methods in selected module
  - Import dependencies
  - Modules that import this module

**Best for:** Interactive exploration and understanding module relationships

**Usage:** Open in a web browser

### 3. `dependencies.json` 📋
Raw JSON data containing:
```json
{
  "module_name": {
    "path": "path/to/file.py",
    "imports": ["list", "of", "imports"],
    "classes": ["Class1", "Class2"],
    "methods_defined": ["method1", "method2"],
    "methods_called": ["external_method"]
  }
}
```

**Best for:** Programmatic analysis and integration with other tools

## Module Structure

### Core Modules (`Core/`)
- `tb_types.py` - Type definitions and enums
- `event.py` - Event class definition
- `event_dispatcher.py` - Event dispatch system
- `order.py` - Order data structure
- `position.py` - Position data structure
- `request.py` - Request types

### Interfaces (`Interfaces/`)
- **WEB/** - HTTP and WebSocket servers
  - `HTTPServer.py` - HTTP server implementation
  - `HTTPClient.py` - HTTP client implementation
  - `WSocServ.py` - WebSocket server
- **SQL/** - Database connections (currently empty)

### Gateway Commands (`GatewayCommand/`)
- `ManagerCommand.py` - Manager communication
- `StratCommand.py` - Strategy command communication (uses HTTPClient)

### Strategies (`Strategies/`)
- `Utils.py` - Utility functions
- `StratTemplate/Temp_MainStrat.py` - Main strategy template (uses Core types and Utils)

### Tracking Engine (`TrackingEngine/`)
- `Tracker.py` - Main tracker that orchestrates strategy and gateway communication

### Entry Point
- `main.py` - Application entry point (initializes HTTPServer and Tracker)

## Key Dependencies

1. **Tracker** → Strategy, GateComm
2. **Strategy** → Core types (Order, EventType, etc.)
3. **GateComm** → HTTPClient
4. **HTTPServer** ↔ HTTPClient (bidirectional communication)
5. **Main** → HTTPServer, Tracker

## Dependency Analysis Scripts

Two Python scripts were used to generate these files:

1. **`analyze_dependencies.py`** - Analyzes imports and method calls using AST
2. **`generate_html_graph.py`** - Creates interactive HTML visualization

You can regenerate these files by running:
```bash
python3 analyze_dependencies.py
python3 generate_html_graph.py
```

## How to Use

### For Quick Understanding
1. Open `dependency_graph.html` in a web browser
2. Click on modules to see their details
3. Use search to find specific modules

### For Documentation
1. Review `dependency_graph.md` for a text-based overview
2. Reference specific modules and their dependencies
3. Share with team members via version control

### For Integration
1. Parse `dependencies.json` for programmatic access
2. Use in build systems or documentation generators
3. Integrate with IDE plugins or analysis tools

---

**Generated on:** 2026-08-29  
**StratConn Repository**
