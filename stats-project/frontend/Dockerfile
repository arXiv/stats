# Node image to use
ARG NODE_VERSION=24
FROM node:${NODE_VERSION}

WORKDIR /app

# Copy all files
COPY . .

# Set build arguments
ARG REACT_APP_API_URL
ARG REACT_APP_ENV

# Set environment variables
ENV REACT_APP_API_URL=$REACT_APP_API_URL
ENV REACT_APP_ENV=$REACT_APP_ENV

# Install dependencies
RUN npm install

# Build the app
RUN npm run build

# Use environment substitution in the built index.html
RUN sed -i 's|%REACT_APP_ENV%|'${REACT_APP_ENV}'|g' build/index.html

# Install serve
RUN npm install -g serve

# Expose port 9000
EXPOSE 9000

# Start the application
CMD ["serve", "-s", "build", "-l", "9000"]