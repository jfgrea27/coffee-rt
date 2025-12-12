FROM maven:3.9-eclipse-temurin-17 AS builder

WORKDIR /app

# Copy pom.xml first for dependency caching
COPY pom.xml .
RUN mvn dependency:go-offline -B

# Copy source and build
COPY src ./src
RUN mvn clean package -DskipTests -B

# Runtime image using Flink
FROM flink:1.18-java17

# Copy the built JAR
COPY --from=builder /app/target/coffee-rt-flink-1.0.0.jar /opt/flink/usrlib/coffee-rt-flink.jar

# Default entry point will be set by docker-compose or kubernetes
# to submit the job to the Flink cluster
