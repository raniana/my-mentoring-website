from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine

Base = declarative_base()


class Mentor(Base):
    __tablename__ = 'mentor'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    

class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String(250))
    role = Column(String(250), nullable=True)
    mentor_id= Column(Integer,nullable=True)
    phone= Column(String(250), nullable=True)

class Task(Base):
    __tablename__ = 'task'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    date = Column(String(250))
    added = Column(String(250), nullable=False)
                                                                                                                                                                                                                                                                           
class StudentTask(Base):
    __tablename__= 'studenttask'

    id= Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    date = Column(String(250))
    student_id= Column(Integer, ForeignKey('user.id'))
    task_id = Column(Integer, ForeignKey('task.id'))
    status = Column(String(250))
    user = relationship(User)
    task = relationship(Task)
    
                       
                            
engine = create_engine('postgrtesql://sudament:sudament@52.15.210.121/sudamendb')
Base.metadata.create_all(engine)
