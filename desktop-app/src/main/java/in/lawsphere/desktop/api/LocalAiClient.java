package in.lawsphere.desktop.api;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.Map;

public final class LocalAiClient {
    private static final URI DEFAULT_BASE_URI = URI.create("http://127.0.0.1:8000");

    private final URI baseUri;
    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;

    public LocalAiClient() {
        this(DEFAULT_BASE_URI);
    }

    public LocalAiClient(URI baseUri) {
        this.baseUri = baseUri;
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(2))
                .build();
        this.objectMapper = new ObjectMapper()
                .setPropertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE);
    }

    public SystemStatus getSystemStatus() {
        return get("/api/v1/system/status", SystemStatus.class);
    }

    public ModelList getModels() {
        return get("/api/v1/models", ModelList.class);
    }

    public AskResponse ask(String question, int limit) {
        HttpRequest request = HttpRequest.newBuilder(baseUri.resolve("/api/v1/search/ask"))
                .timeout(Duration.ofMinutes(4))
                .header("Accept", "application/json")
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(serialize(Map.of(
                        "query", question,
                        "limit", limit))))
                .build();
        try {
            HttpResponse<String> response = httpClient.send(
                    request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() < 200 || response.statusCode() >= 300) {
                throw new AiServiceException("Local AI service returned HTTP " + response.statusCode()
                        + ": " + response.body());
            }
            return objectMapper.readValue(response.body(), AskResponse.class);
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            throw new AiServiceException("Interrupted while waiting for the local answer", exception);
        } catch (IOException exception) {
            throw new AiServiceException("Could not read an answer from the local AI service", exception);
        }
    }

    private String serialize(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (IOException exception) {
            throw new AiServiceException("Could not prepare a request for the local AI service", exception);
        }
    }

    private <T> T get(String path, Class<T> responseType) {
        HttpRequest request = HttpRequest.newBuilder(baseUri.resolve(path))
                .timeout(Duration.ofSeconds(4))
                .header("Accept", "application/json")
                .GET()
                .build();
        try {
            HttpResponse<String> response = httpClient.send(
                    request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() < 200 || response.statusCode() >= 300) {
                throw new AiServiceException("Local AI service returned HTTP " + response.statusCode());
            }
            return objectMapper.readValue(response.body(), responseType);
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            throw new AiServiceException("Interrupted while contacting the local AI service", exception);
        } catch (IOException exception) {
            throw new AiServiceException(
                    "Could not read a response from the local AI service at " + baseUri, exception);
        }
    }
}
