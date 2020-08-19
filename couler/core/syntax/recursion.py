import types
from collections import OrderedDict

from couler.core import pyfunc, states
from couler.core.templates import Step, Steps


def exec_while(condition, inner_while):
    """
    Generate the Argo recursive logic. For example
    https://github.com/argoproj/argo/blob/master/examples/README.md#recursion.
    """
    # _while_lock means 'exec_while' operation begins to work
    # _while_steps stores logic steps inside the recursion logic
    states._while_lock = True

    # Enforce inner function of the while-loop to run
    if isinstance(inner_while, types.FunctionType):
        branch = inner_while()
        if branch is None:
            raise SyntaxError("require function return value")
    else:
        raise TypeError("condition to run would be a function")

    branch_dict = pyfunc.extract_step_return(branch)
    recursive_name = "exec-while-" + branch_dict["name"]
    recursive_id = "exec-while-" + branch_dict["id"]
    if states.workflow.get_template(recursive_name) is None:
        template = Steps(name=recursive_name)
    else:
        raise SyntaxError("Recursive function can not be called twice ")

    # Generate leaving point for recursive
    step_out_name = "%s-%s" % (recursive_name, "exit")
    pre = condition["pre"]
    pre_dict = pyfunc.extract_step_return(pre)
    condition_suffix = condition["condition"]

    # Generate the recursive go to step
    when_prefix = "{{steps.%s.%s}} %s %s" % (
        branch_dict["id"],
        branch_dict["output"],
        condition_suffix,
        pre_dict["value"],
    )
    step_out_template = OrderedDict(
        {
            "name": step_out_name,
            "template": recursive_name,
            "when": when_prefix,
        }
    )
    step_out_id = pyfunc.invocation_name(step_out_name, recursive_id)
    states._while_steps[step_out_id] = [step_out_template]

    # Add steps inside the recursive logic to recursive template
    template.steps = list(states._while_steps.values())

    # Add this recursive logic to the templates
    states.workflow.add_template(template)

    # Add recursive logic to global _steps
    recursive_out_step = Step(name=recursive_id, template=recursive_name)
    states.workflow.add_step(name=recursive_id, step=recursive_out_step)

    states._while_lock = False
    states._while_steps = OrderedDict()
