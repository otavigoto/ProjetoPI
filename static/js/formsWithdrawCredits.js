const tipoConta = document.getElementById('tipoConta');
const chavePix = document.getElementById('chavePix');
const chavePixLabel = document.getElementById('chavePixLabel');

tipoConta.addEventListener('change', function () {
  if (this.value === 'pix') {
    chavePix.style.display = 'block';
    chavePixLabel.style.display = 'block';
  } else {
    chavePix.style.display = 'none';
    chavePixLabel.style.display = 'none';
  }
});