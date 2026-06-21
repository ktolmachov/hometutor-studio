files = [
    'app/user_state_tutor.py',
    'app/user_state_sync.py',
    'app/user_state_research.py',
    'app/user_state_reading.py',
    'app/user_state_quiz.py',
    'app/user_state_flashcards.py'
]

for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    new_content = content.replace('from app.user_state_core import *', 
        'from app.user_state_core import *\\nfrom app.user_state_goals import *\\nfrom app.user_state_lineage import *'.replace('\\n', '\n'))
    
    with open(f, 'w', encoding='utf-8') as file:
        file.write(new_content)
        
    print(f'Updated {f}')
