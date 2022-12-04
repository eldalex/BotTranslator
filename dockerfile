FROM python:3.9

RUN apt update && apt -y install nano python3-pip

RUN mkdir /BotTranslator
RUN mkdir /BotTranslator/database

ENV APP_HOME=/BotTranslator
WORKDIR $APP_HOME

ADD main.py $APP_HOME
ADD cycle.py $APP_HOME
ADD .env $APP_HOME
ADD entrypoint.sh $APP_HOME
ADD requirements.txt $APP_HOME
RUN pip install -r $APP_HOME/requirements.txt

RUN chmod +x $APP_HOME/entrypoint.sh

CMD ["/BotTranslator/entrypoint.sh"]
