# MTG Commander Game - Development Guide

This guide covers development setup, architecture, and contribution guidelines for the MTG Commander Game project.

## 🚀 Quick Development Setup

### Prerequisites
- **Python 3.8+** (3.9+ recommended)
- **Git** for version control
- **Virtual environment** (recommended)

### Setup Steps

1. **Clone and setup environment:**
   ```bash
   git clone <repository-url>
   cd MTG
   python -m venv .venv
   
   # Windows
   .venv\Scripts\activate
   
   # macOS/Linux  
   source .venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   
   # For development tools
   pip install -e .[dev]
   ```

3. **Run the application:**
   ```bash
   python main.py
   ```

4. **Run tests:**
   ```bash
   python tests/test_card_mechanics.py
   ```

## 🏗️ Architecture Overview

The MTG Commander Game follows a modular, layered architecture:

### Core Layers

```
├── 🎮 UI Layer (ui/)
│   ├── Qt-based desktop interface
│   ├── Game board and card rendering
│   └── Player interaction components
│
├── 🎯 Game Logic Layer (engine/)  
│   ├── Game state management
│   ├── Rules engine and validation
│   ├── Card mechanics and abilities
│   ├── Combat and stack systems
│   └── Mana and casting systems
│
├── 🤖 AI Layer (ai/)
│   ├── AI player controllers
│   └── Strategic decision making
│
└── 📊 Data Layer (data/)
    ├── Card database
    ├── Deck definitions
    └── Game configuration
```

### Key Components

#### Game Engine (`engine/`)

- **`GameController`**: Central game flow coordinator
- **`GameState`**: Manages players, battlefield, and game state
- **`RulesEngine`**: Validates moves and enforces Magic rules
- **`CastingSystem`**: Handles spell casting mechanics
- **`CombatManager`**: Combat phase resolution
- **`StackSystem`**: Stack and priority management
- **`AbilitiesSystem`**: Card abilities parsing and execution

#### User Interface (`ui/`)

- **`GameWindow`**: Main application window
- **`GameBoard`**: Interactive game board interface
- **`CardRenderer`**: Card display and interaction
- **`DebugWindow`**: Development debugging tools

#### AI System (`ai/`)

- **`BasicAI`**: Core AI decision-making logic
- **`AIPlayer`**: Enhanced AI behaviors and strategies

## 🔧 Development Workflow

### Adding New Features

1. **Plan the feature:**
   - Identify which layer(s) are affected
   - Check Magic comprehensive rules for compliance
   - Design API interfaces first

2. **Implement incrementally:**
   - Start with core logic in `engine/`
   - Add UI components in `ui/`
   - Update AI behavior if needed
   - Write tests as you go

3. **Test thoroughly:**
   - Unit tests for individual components
   - Integration tests for feature workflows
   - Manual testing with real game scenarios

### Code Style Guidelines

- **Type hints** for all function parameters and returns
- **Docstrings** for all public methods and classes
- **PEP 8** styling (use `black` and `isort`)
- **Descriptive names** for variables and functions
- **Small, focused functions** (single responsibility)

### Testing Strategy

- **Unit tests** for individual methods and classes
- **Integration tests** for component interactions  
- **Scenario tests** for complex game state interactions
- **Regression tests** for bug fixes

## 📝 Adding New Card Mechanics

The game uses a sophisticated ability parsing system. Here's how to add support for new mechanics:

### 1. Define the Ability Structure

```python
# In engine/abilities_system.py
class NewKeywordAbility(KeywordAbility):
    def __init__(self, parameter):
        super().__init__("New Keyword")
        self.parameter = parameter
    
    def apply_effect(self, game_state, source):
        # Implement the mechanic
        pass
```

### 2. Add Parsing Logic

```python
# In engine/rules_engine.py
def parse_new_keyword(text: str):
    pattern = r'new keyword (\d+)'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return NewKeywordAbility(int(match.group(1)))
    return None
```

### 3. Register with Parser

```python
# Add to parse_oracle_text() in rules_engine.py
ability = parse_new_keyword(line)
if ability:
    abilities.append(ability)
    continue
```

### 4. Add Tests

```python
# In tests/test_card_mechanics.py
def test_new_keyword_ability(self):
    card = Card(
        id="test",
        name="Test Card",
        types=["Creature"],
        mana_cost=2,
        text="New keyword 3"
    )
    
    abilities = parse_oracle_text(card.text)
    self.assertEqual(len(abilities), 1)
    self.assertIsInstance(abilities[0], NewKeywordAbility)
    self.assertEqual(abilities[0].parameter, 3)
```

## 🐛 Debugging and Testing

### Debug Tools

- **F9** in-game: Opens debug window showing game state
- **Logging**: Enable with `--no-log` flag (disabled by default)
- **Test Suite**: Run `python tests/test_card_mechanics.py`

### Common Debug Scenarios

1. **Card not playable:**
   - Check `PlayabilityChecker.can_play_card()`
   - Verify mana costs and zone restrictions
   - Check timing restrictions

2. **Ability not triggering:**
   - Verify ability parsing in `parse_oracle_text()`
   - Check trigger registration in `AbilityManager`
   - Ensure proper event firing

3. **UI not updating:**
   - Check event propagation from engine to UI
   - Verify `GameAppAPI` method calls
   - Look for Qt signal/slot connections

### Performance Optimization

- **Profile** with `python -m cProfile main.py`
- **Memory usage** with `memory_profiler`
- **Card database queries** - cache frequently accessed cards
- **UI rendering** - use Qt's efficient painting methods

## 📦 Building and Deployment

### Local Development Build

```bash
# Test the application
python main.py

# Run tests
python tests/test_card_mechanics.py

# Check for issues
python -m flake8 engine/ ui/ ai/
python -m black --check engine/ ui/ ai/
```

### Production Release Build

```bash
# Install build dependencies
pip install pyinstaller

# Create distributable executable
python build_release.py
```

This creates:
- `dist/MTG-Commander.exe` - Standalone executable
- `dist/MTG-Commander-v1.0.0.zip` - Complete release package
- `install.bat` - Windows installer script

### Deployment Checklist

- [ ] All tests passing
- [ ] No lint warnings
- [ ] Documentation updated
- [ ] Version number incremented
- [ ] Release notes written
- [ ] Build tested on clean system

## 🤝 Contributing Guidelines

### Pull Request Process

1. **Fork** the repository
2. **Create feature branch** (`git checkout -b feature/amazing-feature`)
3. **Make changes** following code style guidelines
4. **Add/update tests** for new functionality
5. **Update documentation** as needed
6. **Test thoroughly** - all tests must pass
7. **Submit pull request** with clear description

### Issue Reporting

When reporting bugs or feature requests:

- **Search existing issues** first
- **Provide clear reproduction steps** for bugs
- **Include system information** (OS, Python version)
- **Attach relevant log output** if available
- **Describe expected vs actual behavior**

### Code Review Criteria

- **Functionality**: Does it work as intended?
- **Code quality**: Is it readable and maintainable?
- **Performance**: Are there any obvious performance issues?
- **Security**: Are there any security implications?
- **Testing**: Are there adequate tests?
- **Documentation**: Is the code well-documented?

## 📚 Resources

### Magic: The Gathering Rules
- [Comprehensive Rules](https://magic.wizards.com/en/rules) - Official MTG rules
- [Card Database](https://scryfall.com/) - Complete card information
- [Commander Format](https://mtgcommander.net/index.php/rules/) - Commander-specific rules

### Technical Documentation
- [PySide6 Documentation](https://doc.qt.io/qtforpython/) - Qt GUI framework
- [Python Style Guide](https://pep8.org/) - PEP 8 coding standards
- [Type Hints](https://docs.python.org/3/library/typing.html) - Python typing

### Development Tools
- [PyInstaller](https://pyinstaller.readthedocs.io/) - Python executable bundling
- [pytest](https://docs.pytest.org/) - Testing framework
- [black](https://black.readthedocs.io/) - Code formatting
- [flake8](https://flake8.pycqa.org/) - Code linting

---

## 🎯 Current Development Priorities

Based on the comprehensive Magic rules analysis:

1. **State-Based Actions**: Complete implementation of rule 704
2. **Layer System**: Continuous effects ordering (rule 613)
3. **Advanced Targeting**: Complex targeting scenarios
4. **Replacement Effects**: Priority and interaction rules
5. **Multiplayer Rules**: Enhanced multiplayer game support

---

**Happy Coding!** 🎮✨

For questions or support, please open an issue in the repository.
