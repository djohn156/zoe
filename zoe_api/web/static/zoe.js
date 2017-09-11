function format_bytes(bytes, decimals) {
    if(bytes === 0) {
        document.write('0 Byte');
        return;
    }
    var k = 1000;
    var dm = decimals + 1 || 3;
    var sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    var i = Math.floor(Math.log(bytes) / Math.log(k));
    document.write((bytes / Math.pow(k, i)).toPrecision(dm) + ' ' + sizes[i]);
}
