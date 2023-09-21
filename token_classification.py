# -*- coding: utf-8 -*-
"""Token_Classification.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1GV6FDMREiLjjF1P5NI9mD5bzRyoyrQJC
"""

!pip install transformers

import os
import pandas as pd
import xml.etree.ElementTree as ET


# converts relative filepath into absolute, does not work in notebook
'''def to_absolute(dir):
   return os.path.join(os.path.dirname(__file__), dir)'''

'''def create_label_df(label_dir):
   df = pd.DataFrame(columns=('Filename', 'Date', 'Start', 'End', 'Text', 'Category', 'Value'))
   for parent, dirs, files in os.walk(label_dir):
      for file in files:
         print(f'FILENAME: {file}')
         tree = ET.parse(os.path.join(parent, file))
         root = tree.getroot()
         tags = root[1]
         date = tags.findall('DATE')[0].attrib['text']
         #print(date)
         for tag in tags:
            row = [file, date, tag.attrib['start'], tag.attrib['end'], tag.attrib['text'], tag.tag, tag.attrib['TYPE']]
            df.loc[len(df.index)] = row
   df.to_csv(to_absolute('PHI_NER_Labels.csv'))
   return df'''

def load_record_text(label_dir):
   for parent, dirs, files in os.walk(label_dir):
      for file in files:
         tree = ET.parse(os.path.join(parent, file))
         root = tree.getroot()
         text = root[0].text
         yield file, text
#original
# calculates the overlap between two spans
def calculate_overlap(start1, end1, start2, end2):
   #start1, end1, start2, end2 = map(int, (start1, end1, start2, end2))
   if start1 >= end2 or end1 <= start2:
      return 0
   if start1 <= start2 and end1 >= end2:
      return end2 - start2
   if start1 >= start2 and end1 <= end2:
      return end1 - start1
   if start1 >= start2:
      return end2 - start1
   return end1 - start2


from transformers import BertTokenizerFast
import numpy as np

from transformers import BertForTokenClassification, BertTokenizerFast, Trainer, TrainingArguments, AutoTokenizer,AutoModelForTokenClassification


def load_data(label_dir, df, tokenizer):
   result = []
   tokens=[]
   for filename, text in load_record_text(label_dir):
      df_file = df.loc[df['Filename'] == filename]
      #print(filename)
      #text_tokenized = tokenizer(text, padding='max_length', max_length=512, truncation=True, return_tensors="pt")
      text_tokenized=tokenizer(text,padding=True,return_tensors="pt")
      #text_tokenized= tokenizer(text, return_offsets_mapping=True, padding=True, truncation=True)
      input_ids = text_tokenized['input_ids'][0]
      tokens.append(tokenizer.convert_ids_to_tokens(input_ids))
      result.append([])
      df_list = list(df_file.iterrows())
      for i in range(len(text_tokenized['input_ids'][0])):
         # determine what label to assign this token
         span = text_tokenized.token_to_chars(i)
         label_assigned = False
         for row in df_list:
            if not span:
               break
            # these may need to be decremented by one
            start = row[1][3]
            end = row[1][4]
            label = row[1][6]
            if calculate_overlap(span.start, span.end, start, end) > 0:
               if start >= span.start:
                  result[-1].append(f"B-{label}")
               else:
                  result[-1].append(f"I-{label}")
               label_assigned = True
               break
         if not label_assigned:
            result[-1].append('O')

   return tokens,result

   #print(create_label_df(to_absolute('PHI_Gold')))
   #print(create_label_df(to_absolute('testing-PHI-Gold-fixed')))
df = pd.read_csv('PHI_NER_Labels_Train.csv')
#tokenizer = BertTokenizerFast.from_pretrained('bert-base-cased')
#tokenizer = BertTokenizerFast.from_pretrained("emilyalsentzer/Bio_ClinicalBERT")
#tokens,results=load_data('/content/sample_data/PHI_Gold', df, tokenizer)

#emilyalsentzer/Bio_ClinicalBERT
#prajjwal1/bert-small
#tokenizer = AutoTokenizer.from_pretrained("emilyalsentzer/Bio_ClinicalBERT")
#tokens,results=load_data('/content/sample_data/PHI_Gold', df, tokenizer)
#tokens,results=load_data('PHI_Gold', df, tokenizer)

#print(results[:3][:3])
#print(tokens[:3][:3])

import torch
from transformers import BertForTokenClassification, BertTokenizerFast, Trainer, TrainingArguments, AutoTokenizer,AutoModelForTokenClassification
df_train = pd.read_csv('PHI_NER_Labels_Train.csv')
df_test = pd.read_csv('PHI_NER_Labels_Test.csv')

# Load ClinicalBERT tokenizer
#tokenizer = AutoTokenizer.from_pretrained("bert-base-cased", padding=True, max_length=512)
tokenizer = AutoTokenizer.from_pretrained("emilyalsentzer/Bio_ClinicalBERT", padding=True, max_length=512)



# Load training and test data

train_data,train_labels = load_data('PHI_Gold', df_train, tokenizer)
test_data,test_labels = load_data('testing-PHI-Gold-fixed', df_test, tokenizer)

print("train_labels",train_labels)

unique_tags=set()
for doc in train_labels+test_labels:
  for tag in doc:
    unique_tags.add(tag)

print(unique_tags)
tag2id = {tag: id for id, tag in enumerate(unique_tags)}
id2tag = {id: tag for tag, id in tag2id.items()}

print("tag2id",tag2id)
print(train_labels[:3][:3])

train_encodings = tokenizer(train_data, is_split_into_words=True, return_offsets_mapping=True, padding=True, truncation=True,max_length=512)
test_encodings = tokenizer(test_data, is_split_into_words=True, return_offsets_mapping=True, padding=True, truncation= True,max_length=512)

def encode_tag(tags, encodings):
  labels=[]
  for doc in tags:
     a=[]
     for tag in doc:
       a.append(tag2id[tag])
     labels.append(a)
  encoded_labels = []
  for doc_labels, doc_offset in zip(labels, encodings.offset_mapping):
      doc_enc_labels = np.ones(len(doc_offset), dtype=int) * -100
      arr_offset=np.array(doc_offset)
      start_idxs = np.where((arr_offset[:, 0] == 0) & (arr_offset[:, 1] != 0))[0]
      for idx in start_idxs:
          if idx < len(doc_labels):
              doc_enc_labels[idx] = doc_labels[idx]
      encoded_labels.append(doc_enc_labels.tolist())
  return encoded_labels

train_labels1=encode_tag(train_labels,train_encodings)
test_labels1 = encode_tag(test_labels,test_encodings)


class PHI_Dataset(torch.utils.data.Dataset):
    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels = labels

    def __getitem__(self, idx):
        item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()if key != 'offset_mapping'}
        item['labels'] = torch.tensor(self.labels[idx])
        return item

    def __len__(self):
        return len(self.labels)

print(train_labels1[:3][:])

train_dataset = PHI_Dataset(train_encodings, train_labels1)
test_dataset = PHI_Dataset(test_encodings, test_labels1)

from sklearn.metrics import precision_recall_fscore_support, accuracy_score
from sklearn.metrics import classification_report

def compute_metrics(pred):
    labels = pred.label_ids.flatten()
    preds = pred.predictions.argmax(-1).flatten()
    precision, recall, f1, _ = precision_recall_fscore_support(labels, preds, average='macro')
    acc = accuracy_score(labels, preds)
    label_precision, label_recall, label_f1, _ = precision_recall_fscore_support(labels, preds, average=None)
    class_report = classification_report(labels, preds)
    return {
        'accuracy': acc,
        'f1': f1,
        'precision': precision,
        'recall': recall,
        'label_precision': label_precision,
        'label_recall': label_recall,
        'label_f1': label_f1,
        'classification_report': class_report
    }

def save_model(model, output, EPOCH, filename):
    PATH = f"{filename}.pt"
    torch.save({
                'epoch': EPOCH,
                'model_state_dict': model.state_dict(),
                'train_output': output if output else None,
                }, PATH)

from collections import Counter
flat_labels = []
for row in train_labels1:
    flat_labels += row

label_counts = Counter(flat_labels)
print(label_counts)
Y = np.array([label_counts[id] for id in sorted(label_counts.keys())[1:]])
print(Y)
pos_weights = (Y.sum() - Y) / Y
pos_weights[np.isinf(pos_weights)] = 1
print(pos_weights)
pos_weights = torch.Tensor(pos_weights)
pos_weights.cuda()

from sklearn.utils.class_weight import compute_class_weight
from torch import nn

class_weight = compute_class_weight('balanced', classes=np.unique(flat_labels), y=flat_labels)
class_weight = torch.Tensor(class_weight[1:])
class_weight.cuda()
print(class_weight)

class WeightedTrainer(Trainer):
    def compute_loss(self, model, inputs, return_outputs=False):
        labels = inputs.get("labels")
        # forward pass
        outputs = model(**inputs)
        logits = outputs.get("logits")
        # compute custom loss (suppose one has 3 labels with different weights)
        loss_fct = nn.CrossEntropyLoss(weight=class_weight).cuda()
        #loss_fct = nn.CrossEntropyLoss(weight=pos_weights).cuda()
        loss = loss_fct(logits.view(-1, self.model.config.num_labels), labels.view(-1))
        return (loss, outputs) if return_outputs else loss

from transformers import BertForTokenClassification, BertTokenizerFast, Trainer, TrainingArguments, AutoTokenizer,AutoModelForTokenClassification

model=AutoModelForTokenClassification.from_pretrained("emilyalsentzer/Bio_ClinicalBERT", num_labels=len(unique_tags))

EPOCHS = 20

# Fine-tune ClinicalBERT
# model = BertForTokenClassification.from_pretrained("emilyalsentzer/Bio_ClinicalBERT", num_labels=len(tag2idx))
# Define training arguments
training_args = TrainingArguments(
    output_dir='./results',
    learning_rate=1e-6,
    num_train_epochs=EPOCHS,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=64,
    warmup_steps=500,
    weight_decay=0.01,
    logging_dir='./logs',
    logging_steps=100,
    evaluation_strategy='epoch'
)

# Load a model
checkpoint_path = None
use_cuda = torch.cuda.is_available()
device = torch.device("cuda" if use_cuda else "cpu")
checkpoint = None
if checkpoint_path:
    model.cuda()
    checkpoint = torch.load(checkpoint_path, map_location=device)
    model.load_state_dict(checkpoint['model_state_dict'])

# Define the Trainer object and start training
trainer = WeightedTrainer(
    model=model,
    args=training_args,
    compute_metrics=compute_metrics,
    train_dataset=train_dataset,
    eval_dataset=test_dataset,
    data_collator=lambda data: {'input_ids': torch.stack([item['input_ids'] for item in data]),
'attention_mask': torch.stack([item['attention_mask'] for item in data]),
'labels': torch.stack([item['labels'] for item in data])}
)

output = trainer.train()

trainer.evaluate()

eval_pred = trainer.predict(test_dataset)
#print(eval_pred)
class_report=compute_metrics(eval_pred)
print(class_report)

save_model(model, output, EPOCHS, 'last')

