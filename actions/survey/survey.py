from typing import List

class SurveyItem():

    def __init__(self, item_name:str, next=None, previous=None, is_question=True, **kwargs):
        self.item_name = item_name
        self.is_question = is_question

        # Extract other information from kwargs
        for _,v in kwargs.items():
            if "explain_why" in list(v.keys()):
                self.explain_why = v["explain_why"]
            else:
                self.explain_why = None
            if "rephrased_question" in list(v.keys()):
                self.rephrased_question = v["rephrased_question"]
            else:
                self.rephrased_question = None
            break

        self.next = next
        self.previous = previous

    def __repr__(self):
        return self.item_name


class Survey():
    """ Linked List of Survey Items. """

    def __init__(self, nodes:List[SurveyItem]=None):
        """ Init doubly LinkedList from List of Survey Items."""
        self.head = None
        if nodes is not None:
            node = nodes.pop(0)
            self.head = node
            previous = node
            for elem in nodes:

                if node.item_name.startswith("utter_ask"):
                    node.is_question = True
                else:
                    node.is_question = False

                previous = node

                node.next = elem
                node = node.next
                node.previous = previous
                
            self.head.previous=None

    def __repr__(self):
        node = self.head
        nodes = []
        while node is not None:
            nodes.append(node.item_name)
            node = node.next
        nodes.append("None")
        return " -> ".join(nodes)

    def __iter__(self):
        node = self.head
        while node is not None:
            yield node
            node = node.next

    def length(lst) -> int:
        len = 0
        while lst:
            lst = lst.next
            len += 1
        return len

    def add_first(self, node):
        node.next = self.head
        self.head = node

    def add_last(self, node):
        if self.head is None:
            self.head = node
            return
        for current_node in self:
            pass
        current_node.next = node

    # TODO: Add after, Add before, remove node, ? 


# llist = Survey(nodes = [SurveyItem(item_name="1"), SurveyItem(item_name="2"), SurveyItem(item_name="3")])

# for elem in llist:
#     print(elem.previous, elem, elem.next)