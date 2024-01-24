import gc
import os
from functools import partial
from pathlib import Path

# os.environ["CUDA_VISIBLE_DEVICES"] = "6,7"
os.environ["WANDB_MODE"] = "offline"
import datasets
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from trl import DataCollatorForCompletionOnlyLM, SFTTrainer

from prompt2model.output_annotator import construct_meta_prompt
from prompt2model.prompt_parser import MockPromptSpec, TaskType

model_path = Path(
    "/data/datasets/models/huggingface/lmsys/vicuna-7b-v1.5"
)
ckpt_path = Path("/home/xjia2/p2mss/ckpt")
generated_dataset_path = Path("/home/xjia2/p2mss/generated_datasets")
dataset_path = Path(
    "/home/xjia2/p2mss/generation_tasks_best_3/NI_task034_exp_5/task034_0.6_False_False_5/dataset"
)

prompt_spec = MockPromptSpec(
    task_type=TaskType.TEXT_GENERATION,
    instruction="Your task is to generate an answer to a natural question. In this task, the input is a string that consists of both a question and a context passage. The context is a descriptive passage related to the question and contains the answer. And the question can range from Math, Cultural, Social, Geometry, Biology, History, Sports, Technology, Science, and so on.",  # # noqa E501
    examples="""
[input]="Question: What city did Super Bowl 50 take place in? Context: Super Bowl 50 was an American football game to determine the champion of the National Football League (NFL) for the 2015 season. The American Football Conference (AFC) champion Denver Broncos defeated the National Football Conference (NFC) champion Carolina Panthers 24–10 to earn their third Super Bowl title. The game was played on February 7, 2016, at Levi's Stadium in the San Francisco Bay Area at Santa Clara, California. As this was the 50th Super Bowl, the league emphasized the "golden anniversary" with various gold-themed initiatives, as well as temporarily suspending the tradition of naming each Super Bowl game with Roman numerals (under which the game would have been known as "Super Bowl L"), so that the logo could prominently feature the Arabic numerals 50."
[output]="Santa Clara"

[input]="Question: What river runs through Warsaw? Context: Warsaw (Polish: Warszawa [varˈʂava] ( listen); see also other names) is the capital and largest city of Poland. It stands on the Vistula River in east-central Poland, roughly 260 kilometres (160 mi) from the Baltic Sea and 300 kilometres (190 mi) from the Carpathian Mountains. Its population is estimated at 1.740 million residents within a greater metropolitan area of 2.666 million residents, which makes Warsaw the 9th most-populous capital city in the European Union. The city limits cover 516.9 square kilometres (199.6 sq mi), while the metropolitan area covers 6,100.43 square kilometres (2,355.39 sq mi)."
[output]="Vistula River"

[input]="Question: The Ottoman empire controlled territory on three continents, Africa, Asia and which other? Context: The Ottoman Empire was an imperial state that lasted from 1299 to 1923. During the 16th and 17th centuries, in particular at the height of its power under the reign of Suleiman the Magnificent, the Ottoman Empire was a powerful multinational, multilingual empire controlling much of Southeast Europe, Western Asia, the Caucasus, North Africa, and the Horn of Africa. At the beginning of the 17th century the empire contained 32 provinces and numerous vassal states. Some of these were later absorbed into the empire, while others were granted various types of autonomy during the course of centuries."
[output]="Europe"
"""
    # noqa E501
)

construct_prompt = partial(
    construct_meta_prompt,
    instruction=prompt_spec.instruction,
    examples=prompt_spec.examples,
)

tokenizer = AutoTokenizer.from_pretrained(
    model_path,
    local_files_only=True,
    padding_side="left",
    trust_remote_code=True,
)


def filter_func(example):
    return example["output_col"] is not None and example["input_col"] is not None


# def map_func(example):
#     example["model_input"] = construct_prompt(new_input=example["input_col"])
#     example["model_output"] = example["output_col"]
#     example["text"] = (
#         example["model_input"] + example["model_output"] + tokenizer.eos_token
#     )
#     return example



PROMPT_TEMPLATE = """
A chat between a curious user and an artificial intelligence assistant.
The assistant gives helpful, detailed, and polite answers to the user's questions.
USER: 

{task_instruction}

ASSISTANT: Okay.

USER:

{new_input}

ASSISTANT: The output is

"""

def map_func(example):
    example["model_input"] = PROMPT_TEMPLATE.format(
        task_instruction=prompt_spec.instruction,
        new_input=example["input_col"],
    )
    example["model_output"] = example["output_col"]
    example["text"] = (
        example["model_input"] + example["model_output"] + tokenizer.eos_token
    )
    return example

dataset = datasets.load_from_disk(dataset_path).filter(filter_func)
mapped_dataset = dataset.map(map_func, load_from_cache_file=False)
print(mapped_dataset[1]["text"])
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    device_map="auto",
    torch_dtype=torch.bfloat16,
    use_flash_attention_2=False,
)
response_template_with_context = "ASSISTANT: The output is\n\n"
response_template_ids = tokenizer.encode(
    response_template_with_context, add_special_tokens=False
)[2:]

data_collator = DataCollatorForCompletionOnlyLM(
    response_template_ids, tokenizer=tokenizer
)

training_args = TrainingArguments(
    report_to="wandb",
    do_eval=False,
    save_strategy="epoch",
    output_dir="/data/tir/projects/tir5/users/xjia2/ckpt_1",
    evaluation_strategy="no",
    logging_steps=4,
    num_train_epochs=3,
    per_device_train_batch_size=1,
    seed=42,
)
trainer = SFTTrainer(
    model=model,
    args=training_args,
    train_dataset=mapped_dataset,
    dataset_text_field="text",
    data_collator=data_collator,
    max_seq_length=1000,
)
trainer.train()
del trainer
gc.collect()
torch.cuda.empty_cache()
