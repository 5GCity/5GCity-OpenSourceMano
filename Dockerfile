FROM ubuntu:16.04

WORKDIR /usr/src/app
COPY . /usr/src/app

RUN apt-get update
RUN apt-get install -y npm git python-pip
RUN npm install -g bower
RUN ln -s /usr/bin/nodejs /usr/bin/node
RUN bower install --allow-root
RUN pip install -r requirements.txt


# delete the copy of the database inside the container (if exists)
RUN rm -f db.sqlite3

RUN python manage.py makemigrations sf_user projecthandler instancehandler vimhandler
RUN python manage.py migrate

RUN python manage.py shell -c "from projecthandler.osm_model import OsmProject; from sf_user.models import CustomUser; CustomUser.objects.create_superuser('admin', 'admin'); admin = CustomUser.objects.get(username='admin'); OsmProject.create_project('admin',admin,True, 'project admin','')"


EXPOSE 80
CMD ["python", "manage.py", "runserver", "0.0.0.0:80"]
