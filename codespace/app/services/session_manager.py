from app import db
from app.models.models import Session, File, CollaborationRole, User
import uuid
from datetime import datetime

class SessionManager:
    @staticmethod
    def create_session(owner_id, title, description, visibility, initial_language):
        session_id = str(uuid.uuid4())
        new_session = Session(
            id=session_id,
            owner_id=owner_id,
            title=title,
            description=description,
            visibility=visibility,
            language=initial_language,
            editing_locked=False # По умолчанию разблокировано
        )
        db.session.add(new_session)

        # Добавляем владельца как коллаборатора с ролью 'owner'
        owner_role = CollaborationRole(session_id=session_id, user_id=owner_id, role='owner')
        db.session.add(owner_role)

        # Создаем первый файл для новой сессии
        initial_file = File(
            session_id=session_id,
            name=f'main.{SessionManager.get_file_extension(initial_language)}',
            content=SessionManager.get_default_code(initial_language),
            language=initial_language,
            is_main=True
        )
        db.session.add(initial_file)

        try:
            db.session.commit()
            return session_id
        except Exception as e:
            db.session.rollback()
            print(f"Error creating session: {e}")
            return None

    @staticmethod
    def get_session(session_id):
        return db.session.get(Session, session_id)

    @staticmethod
    def delete_session(session_id):
        session = db.session.get(Session, session_id)
        if session:
            db.session.delete(session)
            db.session.commit()
            return True
        return False

    @staticmethod
    def get_user_role_in_session(session_id, user_id):
        role = db.session.query(CollaborationRole).filter_by(session_id=session_id, user_id=user_id).first()
        return role.role if role else None

    @staticmethod
    def add_collaborator(session_id, user_id, role='viewer'):
        existing_role = db.session.query(CollaborationRole).filter_by(session_id=session_id, user_id=user_id).first()
        if existing_role:
            # Если роль уже существует, обновляем ее, если новая роль имеет более высокие права
            if SessionManager._role_priority(role) > SessionManager._role_priority(existing_role.role):
                existing_role.role = role
                try:
                    db.session.commit()
                    return True
                except Exception as e:
                    db.session.rollback()
                    print(f"Error updating collaborator role: {e}")
                    return False
            else:
                return False

        new_collaboration = CollaborationRole(session_id=session_id, user_id=user_id, role=role)
        db.session.add(new_collaboration)
        try:
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error adding collaborator: {e}")
            return False

    @staticmethod
    def update_collaborator_role(session_id, user_id, new_role):
        role_entry = db.session.query(CollaborationRole).filter_by(session_id=session_id, user_id=user_id).first()
        if role_entry:
            # Не позволяем понизить владельца с 'owner' на что-либо другое
            if role_entry.role == 'owner' and new_role != 'owner':
                return False
            
            role_entry.role = new_role
            try:
                db.session.commit()
                return True
            except Exception as e:
                db.session.rollback()
                print(f"Error updating collaborator role: {e}")
                return False
        return False

    @staticmethod
    def remove_collaborator(session_id, user_id):
        role = db.session.query(CollaborationRole).filter_by(session_id=session_id, user_id=user_id).first()
        if role and role.role != 'owner': # Нельзя удалить владельца через эту функцию
            db.session.delete(role)
            try:
                db.session.commit()
                return True
            except Exception as e:
                db.session.rollback()
                print(f"Error removing collaborator: {e}")
                return False
        return False

    @staticmethod
    def get_session_collaborators_with_users(session_id):
        return db.session.query(CollaborationRole, User).join(User).filter(
            CollaborationRole.session_id == session_id
        ).all()

    @staticmethod
    def get_session_files(session_id):
        return db.session.query(File).filter_by(session_id=session_id).order_by(File.name.asc()).all()

    @staticmethod
    def create_initial_file_for_session(session_id, language):
        default_code = SessionManager.get_default_code(language)
        file_extension = SessionManager.get_file_extension(language)
        initial_file = File(
            session_id=session_id,
            name=f'main.{file_extension}',
            content=default_code,
            language=language,
            is_main=True
        )
        db.session.add(initial_file)
        db.session.commit()
        return initial_file

    @staticmethod
    def get_default_code(language):
        if language == 'python':
            return "print('Hello, CodeShare from Python!')"
        elif language == 'javascript':
            return "console.log('Hello, CodeShare from JavaScript!');"
        elif language == 'java':
            return "public class Main {\n    public static void main(String[] args) {\n        System.out.println(\"Hello, CodeShare from Java!\");\n    }\n}"
        elif language == 'cpp':
            return "#include <iostream>\n\nint main() {\n    std::cout << \"Hello, CodeShare from C++!\" << std::endl;\n    return 0;\n}"
        elif language == 'csharp':
            return "using System;\n\npublic class Program\n{\n    public static void Main(string[] args)\n    {\n        Console.WriteLine(\"Hello, CodeShare from C#!\");\n    }\n}"
        elif language == 'go':
            return "package main\n\nimport \"fmt\"\n\nfunc main() {\n    fmt.Println(\"Hello, CodeShare from Go!\")\n}"
        elif language == 'rust':
            return "fn main() {\n    println!(\"Hello, CodeShare from Rust!\");\n}"
        else:
            return "// Hello, CodeShare!"

    @staticmethod
    def get_file_extension(language):
        extensions = {
            'python': 'py',
            'javascript': 'js',
            'java': 'java',
            'cpp': 'cpp',
            'csharp': 'cs',
            'go': 'go',
            'rust': 'rs',
            'plaintext': 'txt'
        }
        return extensions.get(language, 'txt')

    @staticmethod
    def _role_priority(role):
        """Вспомогательная функция для определения приоритета роли."""
        if role == 'owner': return 3
        if role == 'editor': return 2
        if role == 'viewer': return 1
        return 0