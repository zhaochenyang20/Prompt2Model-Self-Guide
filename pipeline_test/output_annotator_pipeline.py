"""Test Input Generator."""

from prompt2model.output_annotator import PromptBasedOutputAnnotator
from prompt2model.prompt_parser import MockPromptSpec, TaskType

prompt_spec = MockPromptSpec(
    task_type=TaskType.TEXT_GENERATION,
    instruction="Your task is to generate an answer to a natural question. In this task, the input is a question string. and the output is the corresponding answer string. The questions can range from Math, Cultural, Social, Geometry, Biology, History, Sports, Technology, Science, and so on.",  # # noqa E501
    examples="""input="Question: What is the capital city of China?", output="Beijing"\n\ninput="Question: When was People's Republic of China founded?", output="October 1, 1949"\n\n""",  # noqa E501
)

output_annotator = PromptBasedOutputAnnotator(
    pretrained_model_name="sshleifer/tiny-gpt2"
    # meta-llama/Llama-2-7b-chat-hf
)

prompt = output_annotator.construct_prompt(
    instruction=prompt_spec.instruction,
    input="What's the capital city of China?",
    few_shot_example_string=prompt_spec.examples,
    context_cutoff=3500,
)

# inputs = [
#     "What's the capital city of China?",
#     "What's the capital city of United States?",
# ]

# output_dataset = output_annotator.annotate_outputs(
#     input_strings=inputs,
#     num_candidate_outputs=2,
#     prompt_spec=prompt_spec,
# )