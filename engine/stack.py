class StackItem:
    def __init__(self, source_card, effect, controller_id, targets=None):
        self.source_card = source_card
        self.effect = effect
        self.controller_id = controller_id
        self.targets = targets or []
    def resolve(self, game):
        self.effect(game, self)

class Stack:
    def __init__(self):
        self.items = []
    def push(self, item):
        self.items.append(item)
    def can_resolve(self):
        return len(self.items) > 0
    def resolve_top(self, game):
        if self.items:
            item = self.items.pop()
            item.resolve(game)
