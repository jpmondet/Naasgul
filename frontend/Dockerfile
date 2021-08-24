FROM node:16.3.0-stretch-slim as buildimage

ARG apipath

COPY . /

#RUN npm install html-minifier-terser terser -g \
RUN sed -i "s/apiUrl = \"http:\/\/127.0.0.1\/api\"/apiUrl = $(printf '%s\n' \"$apipath\" | sed -e 's/[\/&]/\\&/g')/g" /automapping-script.js \
      && npm install html-minifier-terser terser -g \
      && html-minifier-terser --collapse-whitespace --remove-comments --remove-optional-tags --remove-redundant-attributes --remove-script-type-attributes --remove-tag-whitespace --use-short-doctype --minify-css true --minify-js true index.html -o public-html/index.html \
      && html-minifier-terser --collapse-whitespace --remove-comments --remove-optional-tags --remove-redundant-attributes --remove-script-type-attributes --remove-tag-whitespace --use-short-doctype --minify-css true --minify-js true background.css -o public-html/background.min.css \
      && html-minifier-terser --collapse-whitespace --remove-comments --remove-optional-tags --remove-redundant-attributes --remove-script-type-attributes --remove-tag-whitespace --use-short-doctype --minify-css true --minify-js true layout.css -o public-html/layout.min.css \
      && html-minifier-terser --collapse-whitespace --remove-comments --remove-optional-tags --remove-redundant-attributes --remove-script-type-attributes --remove-tag-whitespace --use-short-doctype --minify-css true --minify-js true style.css -o public-html/style.min.css \
      && terser /automapping-script.js -o public-html/automapping-script.min.js \
      && terser /service-worker.js -o public-html/service-worker.min.js 

FROM httpd:2.4 as runimage
COPY --from=buildimage /public-html/ /usr/local/apache2/htdocs/
