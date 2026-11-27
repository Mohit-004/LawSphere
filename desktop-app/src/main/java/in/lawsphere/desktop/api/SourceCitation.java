package in.lawsphere.desktop.api;

public record SourceCitation(
        String documentId,
        int chunkId,
        int chunkIndex,
        String title,
        String source,
        String documentType,
        String text,
        int startOffset,
        int endOffset,
        Integer pageNumber,
        double score) {
}
