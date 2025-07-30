FROM python:slim


WORKDIR /home/ai_vocab_bot

COPY requirements.txt .
RUN pip install -r requirements.txt

#COPY . .

#RUN chmod +x /home/ai_vocab_bot/run.sh


#ENTRYPOINT ["/home/ai_vocab_bot/run.sh"]

ENTRYPOINT ["python3", "main.py"]