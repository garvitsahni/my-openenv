import docx

doc = docx.Document('WorkBench_PRD_and_BuildPrompt.docx')
with open('prd.txt', 'w', encoding='utf-8') as f:
    for p in doc.paragraphs:
        f.write(p.text + '\n')
